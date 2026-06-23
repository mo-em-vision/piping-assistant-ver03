export const constants = {
  appName: 'Engineering Knowledge Graph Assistant',
  defaultBackendUrl: 'http://localhost:8000',
} as const

export const backendConfig = {
  healthPath: '/health',
  startupTimeoutMs: 30_000,
  healthPollIntervalMs: 500,
  healthRequestTimeoutMs: 2_000,
  defaultPort: 8000,
  defaultHost: '127.0.0.1',
} as const

export type BackendStatus = 'stopped' | 'starting' | 'connected' | 'error'

export interface BackendStatusPayload {
  status: BackendStatus
  detail?: string
  url: string
}

export function parseBackendUrl(url: string): { host: string; port: number } {
  const parsed = new URL(url)
  const port = parsed.port
    ? Number(parsed.port)
    : parsed.protocol === 'https:'
      ? 443
      : backendConfig.defaultPort

  return {
    host: parsed.hostname || backendConfig.defaultHost,
    port,
  }
}

export function buildHealthUrl(baseUrl: string): string {
  const normalized = baseUrl.replace(/\/$/, '')
  return `${normalized}${backendConfig.healthPath}`
}
