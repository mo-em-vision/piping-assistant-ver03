import type { ChildProcess } from 'node:child_process'

import { randomUUID } from 'node:crypto'
import { execSync } from 'node:child_process'
import { spawn } from 'node:child_process'



import {

  backendConfig,

  buildHealthUrl,

  parseBackendUrl,

  type BackendStatus,

  type BackendStatusPayload,

} from '../../src/config/constants'

import { logAppEvent } from './appLogger'
import type { BackendDevFlags } from './backendDevFlags'
import { resolvePythonExecutable } from './pythonRuntime'



type StatusListener = (payload: BackendStatusPayload) => void



function delay(ms: number): Promise<void> {

  return new Promise((resolve) => {

    setTimeout(resolve, ms)

  })

}



async function checkHealth(baseUrl: string, expectedInstanceId?: string): Promise<boolean> {

  try {

    const response = await fetch(buildHealthUrl(baseUrl), {

      signal: AbortSignal.timeout(backendConfig.healthRequestTimeoutMs),

    })

    if (!response.ok) {

      return false

    }

    if (!expectedInstanceId) {

      return true

    }

    const payload = (await response.json()) as { instance_id?: string }

  const matched = payload.instance_id === expectedInstanceId

  // #region agent log

  if (!matched) {

    fetch('http://127.0.0.1:7445/ingest/50b71ef1-acb8-48e4-9a72-8a7cf07970d2', {

      method: 'POST',

      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '12f291' },

      body: JSON.stringify({

        sessionId: '12f291',

        hypothesisId: 'G',

        location: 'backendProcess.ts:checkHealth',

        message: 'instance_id handshake mismatch',

        data: { expected: expectedInstanceId, received: payload.instance_id ?? null },

        timestamp: Date.now(),

      }),

    }).catch(() => {})

  }

  // #endregion

  return matched

  } catch {

    return false

  }

}



function freePortListeners(port: number): void {

  if (process.platform !== 'win32') {

    return

  }

  try {

    const output = execSync(`netstat -ano | findstr :${port}`, { encoding: 'utf8' })

    const pids = new Set<string>()

    for (const line of output.split('\n')) {

      if (!line.includes('LISTENING')) {

        continue

      }

      const pid = line.trim().split(/\s+/).pop()

      if (pid && pid !== '0') {

        pids.add(pid)

      }

    }

    for (const pid of pids) {

      execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' })

    }

  } catch {

    // No listeners or already free.

  }

}



export class BackendProcessService {

  private process: ChildProcess | null = null

  private status: BackendStatus = 'stopped'

  private detail: string | undefined

  private readonly instanceId = randomUUID()

  private readonly listeners = new Set<StatusListener>()



  constructor(
    private readonly repoRoot: string,
    private readonly backendUrl: string,
    private readonly userDataPath?: string,
    private readonly devFlags: BackendDevFlags = { enableDevInspection: false },
    private readonly freePortOnStart = false,
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

    if (this.freePortOnStart) {

      freePortListeners(port)

    }



    this.process = spawn(python, ['-m', 'api.server'], {

      cwd: this.repoRoot,

      env: {

        ...process.env,

        BACKEND_HOST: host,

        BACKEND_PORT: String(port),

        BACKEND_INSTANCE_ID: this.instanceId,

        PROJECT_ROOT: this.repoRoot,

        ...(this.userDataPath ? { DESKTOP_USER_DATA: this.userDataPath } : {}),
        ...(this.devFlags.enableDevInspection ? { DEV_INSPECTION_ENABLED: '1' } : {}),

      },

      stdio: ['ignore', 'pipe', 'pipe'],

    })



    this.process.on('error', (error) => {

      this.setStatus('error', error.message)

    })



    this.process.on('exit', (code, signal) => {

      if (this.status === 'starting') {

        this.setStatus(

          'error',

          `Backend failed to start (code ${code ?? 'null'}, signal ${signal ?? 'null'}). Another process may be using port ${port}.`,

        )

      } else if (this.status === 'connected') {

        this.setStatus('error', `Backend exited unexpectedly (code ${code ?? 'null'}, signal ${signal ?? 'null'})`)

      }

      this.process = null

    })



    this.process.stderr?.on('data', (chunk: Buffer) => {
      const message = chunk.toString().trim()
      if (message) {
        logAppEvent('warn', 'Backend stderr', message)
        if (this.status !== 'connected') {
          this.detail = message
          this.emit()
        }
      }
    })



    const deadline = Date.now() + backendConfig.startupTimeoutMs



    while (Date.now() < deadline) {

      if (await checkHealth(this.backendUrl, this.instanceId)) {

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


