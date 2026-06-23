import { contextBridge, ipcRenderer } from 'electron'

import type { BackendStatusPayload } from '../src/config/constants'

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  getBackendStatus: (): Promise<BackendStatusPayload | null> =>
    ipcRenderer.invoke('backend:getStatus'),
  retryBackendConnection: (): Promise<BackendStatusPayload | null> =>
    ipcRenderer.invoke('backend:retry'),
  onBackendStatusChange: (callback: (status: BackendStatusPayload) => void): (() => void) => {
    const listener = (_event: Electron.IpcRendererEvent, status: BackendStatusPayload) => {
      callback(status)
    }

    ipcRenderer.on('backend:status', listener)

    return () => {
      ipcRenderer.removeListener('backend:status', listener)
    }
  },
})
