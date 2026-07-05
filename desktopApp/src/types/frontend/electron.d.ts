import type { BackendStatusPayload, GraphExplorerStatusPayload } from '@/config/constants'

export interface WindowDisplayStatePayload {
  isFullScreen: boolean
}

export interface ElectronAPI {
  platform: NodeJS.Platform
  getBackendStatus: () => Promise<BackendStatusPayload | null>
  retryBackendConnection: () => Promise<BackendStatusPayload | null>
  onBackendStatusChange: (callback: (status: BackendStatusPayload) => void) => () => void
  getWindowDisplayState: () => Promise<WindowDisplayStatePayload>
  onWindowDisplayStateChange: (callback: (state: WindowDisplayStatePayload) => void) => () => void
  syncDevMode?: (active: boolean) => Promise<GraphExplorerStatusPayload | null>
  getGraphExplorerStatus?: () => Promise<GraphExplorerStatusPayload | null>
  onGraphExplorerStatusChange?: (callback: (status: GraphExplorerStatusPayload) => void) => () => void
  openStudioWindow?: () => Promise<void>
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}

export {}
