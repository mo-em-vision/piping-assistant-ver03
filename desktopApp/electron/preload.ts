import { contextBridge, ipcRenderer } from 'electron'

import type { BackendStatusPayload } from '../src/config/constants'

export interface WindowDisplayStatePayload {
  isFullScreen: boolean
}

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  getBackendStatus: (): Promise<BackendStatusPayload | null> =>
    ipcRenderer.invoke('backend:getStatus'),
  retryBackendConnection: (): Promise<BackendStatusPayload | null> =>
    ipcRenderer.invoke('backend:retry'),
  getWindowDisplayState: (): Promise<WindowDisplayStatePayload> =>
    ipcRenderer.invoke('window:getDisplayState'),
  onBackendStatusChange: (callback: (status: BackendStatusPayload) => void): (() => void) => {
    const listener = (_event: Electron.IpcRendererEvent, status: BackendStatusPayload) => {
      callback(status)
    }

    ipcRenderer.on('backend:status', listener)

    return () => {
      ipcRenderer.removeListener('backend:status', listener)
    }
  },
  onWindowDisplayStateChange: (
    callback: (state: WindowDisplayStatePayload) => void,
  ): (() => void) => {
    const listener = (_event: Electron.IpcRendererEvent, state: WindowDisplayStatePayload) => {
      callback(state)
    }

    ipcRenderer.on('window:displayState', listener)

    return () => {
      ipcRenderer.removeListener('window:displayState', listener)
    }
  },
})
