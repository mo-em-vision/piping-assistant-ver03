import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron'
import path from 'node:path'

import { constants } from '../src/config/constants'
import { createApplicationMenu } from './menu'
import { getLogDirectory, initAppLogger, logAppEvent } from './services/appLogger'
import type { BackendProcessService } from './services/backendProcess'
import { normalizeDevServerUrl } from './services/devServer'
import { GraphExplorerProcessService } from './services/graphExplorerProcess'
import { runStartup } from './services/startup'
import { closeStudioWindow, openStudioWindow } from './services/studioWindow'

const isDev = !app.isPackaged

let mainWindow: BrowserWindow | null = null
let backendService: BackendProcessService | null = null
let graphExplorerService: GraphExplorerProcessService | null = null

function sendBackendStatus(): void {
  if (!mainWindow || !backendService) {
    return
  }

  mainWindow.webContents.send('backend:status', backendService.getStatus())
}

function sendWindowDisplayState(): void {
  if (!mainWindow) {
    return
  }

  mainWindow.webContents.send('window:displayState', {
    isFullScreen: mainWindow.isFullScreen(),
  })
}

async function loadRenderer(window: BrowserWindow): Promise<void> {
  const devServerUrl = process.env.VITE_DEV_SERVER_URL

  if (isDev && devServerUrl) {
    const url = normalizeDevServerUrl(devServerUrl)
    await window.loadURL(url)
    return
  }

  await window.loadFile(path.join(__dirname, '../dist/index.html'))
}

async function createWindow(): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    show: false,
    title: 'Engineering Workspace',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.on('enter-full-screen', sendWindowDisplayState)
  mainWindow.on('leave-full-screen', sendWindowDisplayState)

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url)
    return { action: 'deny' }
  })

  await loadRenderer(mainWindow)
  sendWindowDisplayState()
}

function sendGraphExplorerStatus(): void {
  if (!mainWindow || !graphExplorerService) {
    return
  }

  mainWindow.webContents.send('graphExplorer:status', graphExplorerService.getStatus())
}

function registerIpcHandlers(): void {
  ipcMain.handle('backend:getStatus', () => backendService?.getStatus() ?? null)

  ipcMain.handle('backend:retry', async () => {
    if (!backendService) {
      return null
    }

    const status = await backendService.retry()
    sendBackendStatus()
    return status
  })

  ipcMain.handle('graphExplorer:getStatus', () => graphExplorerService?.getStatus() ?? null)

  ipcMain.handle('devMode:sync', async (_event, active: boolean) => {
    if (!graphExplorerService) {
      return null
    }

    if (active) {
      const status = await graphExplorerService.start()
      sendGraphExplorerStatus()
      return status
    }

    await graphExplorerService.stop()
    closeStudioWindow()
    sendGraphExplorerStatus()
    return graphExplorerService.getStatus()
  })

  ipcMain.handle('studio:open', async () => {
    await openStudioWindow(isDev, process.env.VITE_DEV_SERVER_URL)
  })

  ipcMain.handle('window:getDisplayState', () => ({
    isFullScreen: mainWindow?.isFullScreen() ?? false,
  }))
}

function buildDiagnostics(): string {
  const status = backendService?.getStatus()
  return [
    `Application: ${constants.appName}`,
    `Version: ${app.getVersion()}`,
    `Platform: ${process.platform}`,
    `Packaged: ${app.isPackaged}`,
    `Logs: ${getLogDirectory()}`,
    `Backend status: ${status?.status ?? 'unknown'}`,
    `Backend url: ${status?.url ?? 'n/a'}`,
    status?.detail ? `Backend detail: ${status.detail}` : null,
  ]
    .filter(Boolean)
    .join('\n')
}

async function bootstrap(): Promise<void> {
  createApplicationMenu({
    getMainWindow: () => mainWindow,
    getDiagnostics: buildDiagnostics,
  })
  registerIpcHandlers()

  logAppEvent('info', 'Starting application bootstrap')

  graphExplorerService = new GraphExplorerProcessService(app.getPath('userData'))
  graphExplorerService.onStatusChange(() => {
    sendGraphExplorerStatus()
  })

  const backendPromise = runStartup((payload) => {
    logAppEvent('info', 'Backend status changed', `${payload.status}${payload.detail ? ` (${payload.detail})` : ''}`)
    sendBackendStatus()
  })

  await createWindow()

  backendService = await backendPromise
  sendBackendStatus()
  logAppEvent('info', 'Application bootstrap complete')
}

void app.whenReady().then(async () => {
  try {
    initAppLogger(app.getPath('userData'))
    await bootstrap()
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    logAppEvent('error', 'Application startup failed', message)
    console.error('Application startup failed:', error)
    await dialog.showErrorBox('Startup failed', message)
    app.quit()
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      void bootstrap().catch((error) => {
        console.error('Failed to recreate window:', error)
      })
    }
  })
})

app.on('before-quit', () => {
  void backendService?.stop()
  void graphExplorerService?.stop()
  closeStudioWindow()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
