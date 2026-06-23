import type { BackendStatusPayload } from '@/config/constants'

export interface ElectronAPI {
  platform: NodeJS.Platform
  getBackendStatus: () => Promise<BackendStatusPayload | null>
  retryBackendConnection: () => Promise<BackendStatusPayload | null>
  onBackendStatusChange: (callback: (status: BackendStatusPayload) => void) => () => void
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}

export {}
