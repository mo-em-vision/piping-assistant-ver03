import type { ChildProcess } from 'node:child_process'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'

import {
  backendConfig,
  buildHealthUrl,
  parseBackendUrl,
  type BackendStatus,
  type BackendStatusPayload,
} from '../../src/config/constants'

type StatusListener = (payload: BackendStatusPayload) => void

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function resolvePythonExecutable(repoRoot: string): string {
  const windowsVenv = path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
  if (existsSync(windowsVenv)) {
    return windowsVenv
  }

  const unixVenv = path.join(repoRoot, '.venv', 'bin', 'python')
  if (existsSync(unixVenv)) {
    return unixVenv
  }

  return process.platform === 'win32' ? 'python' : 'python3'
}

async function checkHealth(baseUrl: string): Promise<boolean> {
  try {
    const response = await fetch(buildHealthUrl(baseUrl), {
      signal: AbortSignal.timeout(backendConfig.healthRequestTimeoutMs),
    })
    return response.ok
  } catch {
    return false
  }
}

export class BackendProcessService {
  private process: ChildProcess | null = null
  private status: BackendStatus = 'stopped'
  private detail: string | undefined
  private readonly listeners = new Set<StatusListener>()

  constructor(
    private readonly repoRoot: string,
    private readonly backendUrl: string,
  ) {}

  getStatus(): BackendStatusPayload {
    return {
      status: this.status,
      detail: this.detail,
      url: this.backendUrl,
    }
  }

  onStatusChange(listener: StatusListener): () => void {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  async start(): Promise<BackendStatusPayload> {
    if (this.status === 'connected') {
      return this.getStatus()
    }

    this.setStatus('starting', 'Launching backend process')

    const { host, port } = parseBackendUrl(this.backendUrl)
    const python = resolvePythonExecutable(this.repoRoot)
    const moduleArgs = ['-m', 'api.health_server']

    this.process = spawn(python, moduleArgs, {
      cwd: this.repoRoot,
      env: {
        ...process.env,
        BACKEND_HOST: host,
        BACKEND_PORT: String(port),
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    this.process.on('error', (error) => {
      this.setStatus('error', error.message)
    })

    this.process.on('exit', (code, signal) => {
      if (this.status === 'connected') {
        this.setStatus('error', `Backend exited unexpectedly (code ${code ?? 'null'}, signal ${signal ?? 'null'})`)
      }
      this.process = null
    })

    this.process.stderr?.on('data', (chunk: Buffer) => {
      const message = chunk.toString().trim()
      if (message && this.status !== 'connected') {
        this.detail = message
        this.emit()
      }
    })

    const deadline = Date.now() + backendConfig.startupTimeoutMs

    while (Date.now() < deadline) {
      if (await checkHealth(this.backendUrl)) {
        this.setStatus('connected')
        return this.getStatus()
      }

      if (this.status === 'error') {
        return this.getStatus()
      }

      await delay(backendConfig.healthPollIntervalMs)
    }

    this.setStatus('error', 'Timed out waiting for backend health check')
    return this.getStatus()
  }

  async retry(): Promise<BackendStatusPayload> {
    await this.stop()
    return this.start()
  }

  async stop(): Promise<void> {
    if (!this.process) {
      this.setStatus('stopped')
      return
    }

    const child = this.process
    this.process = null

    if (!child.killed) {
      child.kill()
    }

    this.setStatus('stopped')
  }

  private setStatus(status: BackendStatus, detail?: string): void {
    this.status = status
    this.detail = detail
    this.emit()
  }

  private emit(): void {
    const payload = this.getStatus()
    for (const listener of this.listeners) {
      listener(payload)
    }
  }
}
