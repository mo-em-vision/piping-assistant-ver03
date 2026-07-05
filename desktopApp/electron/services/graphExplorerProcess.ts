import type { ChildProcess } from 'node:child_process'
import { spawn } from 'node:child_process'

import {
  backendConfig,
  buildHealthUrl,
  constants,
  type GraphExplorerStatus,
  type GraphExplorerStatusPayload,
} from '../../src/config/constants'
import { logAppEvent } from './appLogger'
import { resolvePythonExecutable } from './pythonRuntime'
import { resolveRepoRoot } from './startup'

type StatusListener = (payload: GraphExplorerStatusPayload) => void

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
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

function isBenignGraphExplorerStderr(message: string): boolean {
  return (
    message.includes('_ProactorBasePipeTransport._call_connection_lost') ||
    message.includes('ConnectionResetError') ||
    message.includes('WinError 10054') ||
    message.includes('forcibly closed by the remote host')
  )
}

export class GraphExplorerProcessService {
  private process: ChildProcess | null = null
  private status: GraphExplorerStatus = 'stopped'
  private detail: string | undefined
  private readonly listeners = new Set<StatusListener>()
  private readonly baseUrl = constants.graphExplorerUrl

  constructor(private readonly userDataPath?: string) {}

  getStatus(): GraphExplorerStatusPayload {
    return {
      status: this.status,
      detail: this.detail,
      url: this.baseUrl,
    }
  }

  onStatusChange(listener: StatusListener): () => void {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  async start(): Promise<GraphExplorerStatusPayload> {
    if (this.status === 'connected' && this.process) {
      return this.getStatus()
    }

    if (this.process) {
      await this.stop()
    }

    if (await checkHealth(this.baseUrl)) {
      this.setStatus(
        'error',
        'Port 8765 is in use by a stale graph explorer. Stop that process, then toggle Dev Mode again.',
      )
      return this.getStatus()
    }

    this.setStatus('starting', 'Launching graph explorer')

    const repoRoot = resolveRepoRoot()
    const python = resolvePythonExecutable(repoRoot)

    this.process = spawn(python, ['-m', 'dev.graph_explorer'], {
      cwd: repoRoot,
      env: {
        ...process.env,
        PROJECT_ROOT: repoRoot,
        PYTHONPATH: repoRoot,
        GRAPH_EXPLORER_HOST: '127.0.0.1',
        GRAPH_EXPLORER_PORT: '8765',
        ...(this.userDataPath ? { DESKTOP_USER_DATA: this.userDataPath } : {}),
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: process.platform === 'win32',
    })

    this.process.on('error', (error) => {
      this.setStatus('error', error.message)
    })

    this.process.on('exit', (code, signal) => {
      if (this.status === 'connected') {
        this.setStatus('error', `Graph explorer exited (code ${code ?? 'null'}, signal ${signal ?? 'null'})`)
      } else if (this.status !== 'stopped') {
        this.setStatus('stopped')
      }
      this.process = null
    })

    this.process.stderr?.on('data', (chunk: Buffer) => {
      const message = chunk.toString().trim()
      if (!message || isBenignGraphExplorerStderr(message)) {
        return
      }
      logAppEvent('warn', 'Graph explorer stderr', message)
      if (this.status !== 'connected') {
        this.detail = message
        this.emit()
      }
    })

    const deadline = Date.now() + backendConfig.startupTimeoutMs
    while (Date.now() < deadline) {
      if (await checkHealth(this.baseUrl)) {
        this.setStatus('connected')
        return this.getStatus()
      }
      if (this.status === 'error') {
        return this.getStatus()
      }
      await delay(backendConfig.healthPollIntervalMs)
    }

    this.setStatus('error', 'Timed out waiting for graph explorer health check')
    return this.getStatus()
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

  private setStatus(status: GraphExplorerStatus, detail?: string): void {
    this.status = status
    if (status === 'connected') {
      this.detail = undefined
    } else if (detail !== undefined) {
      this.detail = detail
    }
    this.emit()
  }

  private emit(): void {
    const payload = this.getStatus()
    for (const listener of this.listeners) {
      listener(payload)
    }
  }
}
