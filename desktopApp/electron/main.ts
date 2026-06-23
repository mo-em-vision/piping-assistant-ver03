import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron'
import path from 'node:path'

import { createApplicationMenu } from './menu'
import type { BackendProcessService } from './services/backendProcess'
import { normalizeDevServerUrl } from './services/devServer'
import { runStartup } from './services/startup'

const isDev = !app.isPackaged

let mainWindow: BrowserWindow | null = null
let backendService: BackendProcessService | null = null

function sendBackendStatus(): void {
  if (!mainWindow || !backendService) {
    return
  }

  mainWindow.webContents.send('backend:status', backendService.getStatus())
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

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url)
    return { action: 'deny' }
  })

  await loadRenderer(mainWindow)
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
}

async function bootstrap(): Promise<void> {
  createApplicationMenu(() => mainWindow)
  registerIpcHandlers()

  const backendPromise = runStartup(() => {
    sendBackendStatus()
  })

  await createWindow()

  backendService = await backendPromise
  sendBackendStatus()
}

void app.whenReady().then(async () => {
  try {
    await bootstrap()
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
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
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
