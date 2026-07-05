import { contextBridge, ipcRenderer } from 'electron'

import type { BackendStatusPayload, GraphExplorerStatusPayload } from '../src/config/constants'

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
  syncDevMode: (active: boolean): Promise<GraphExplorerStatusPayload | null> =>
    ipcRenderer.invoke('devMode:sync', active),
  getGraphExplorerStatus: (): Promise<GraphExplorerStatusPayload | null> =>
    ipcRenderer.invoke('graphExplorer:getStatus'),
  openStudioWindow: (): Promise<void> => ipcRenderer.invoke('studio:open'),
  onBackendStatusChange: (callback: (status: BackendStatusPayload) => void): (() => void) => {
    const listener = (_event: Electron.IpcRendererEvent, status: BackendStatusPayload) => {
      callback(status)
    }

    ipcRenderer.on('backend:status', listener)

    return () => {
      ipcRenderer.removeListener('backend:status', listener)
    }
  },
  onGraphExplorerStatusChange: (
    callback: (status: GraphExplorerStatusPayload) => void,
  ): (() => void) => {
    const listener = (_event: Electron.IpcRendererEvent, status: GraphExplorerStatusPayload) => {
      callback(status)
    }

    ipcRenderer.on('graphExplorer:status', listener)

    return () => {
      ipcRenderer.removeListener('graphExplorer:status', listener)
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
