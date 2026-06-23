import { app, BrowserWindow, ipcMain, shell } from 'electron'
import path from 'node:path'

import { createApplicationMenu } from './menu'
import type { BackendProcessService } from './services/backendProcess'
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

function createWindow(): void {
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

  if (isDev && process.env.VITE_DEV_SERVER_URL) {
    void mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    void mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }
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

void app.whenReady().then(async () => {
  createApplicationMenu(() => mainWindow)
  registerIpcHandlers()
  createWindow()

  backendService = await runStartup(() => {
    sendBackendStatus()
  })

  sendBackendStatus()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
      sendBackendStatus()
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
