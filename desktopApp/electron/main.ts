import { appendFileSync } from 'node:fs'
import {
  app,
  BrowserWindow,
  dialog,
  ipcMain,
  shell,
  type WebContentsConsoleMessageEventParams,
} from 'electron'
import path from 'node:path'

import { constants } from '../src/config/constants'

// #region agent log
function agentDebugLog(
  location: string,
  message: string,
  data: Record<string, unknown>,
  hypothesisId: string,
): void {
  try {
    const line =
      JSON.stringify({
        sessionId: 'ed32ea',
        location,
        message,
        data,
        timestamp: Date.now(),
        hypothesisId,
      }) + '\n'
    appendFileSync(path.resolve(__dirname, '../../debug-ed32ea.log'), line, { flag: 'a' })
  } catch {
    // ignore logging failures
  }
}
// #endregion
import { createApplicationMenu } from './menu'
import { getLogDirectory, initAppLogger, logAppEvent } from './services/appLogger'
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

  // #region agent log
  agentDebugLog('electron/main.ts:loadRenderer:start', 'Loading renderer', {
    isDev,
    devServerUrl: devServerUrl ?? null,
  }, 'C')
  // #endregion

  if (isDev && devServerUrl) {
    const url = normalizeDevServerUrl(devServerUrl)
    await window.loadURL(url)
    // #region agent log
    agentDebugLog('electron/main.ts:loadRenderer:dev-done', 'Dev renderer URL loaded', { url }, 'C')
    // #endregion
    return
  }

  await window.loadFile(path.join(__dirname, '../dist/index.html'))
  // #region agent log
  agentDebugLog('electron/main.ts:loadRenderer:prod-done', 'Production index.html loaded', {}, 'C')
  // #endregion
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
    // #region agent log
    agentDebugLog('electron/main.ts:ready-to-show', 'Electron window ready-to-show, showing window', {}, 'C')
    // #endregion
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

  // #region agent log
  // Electron 43+: console-message no longer passes level/message/line/sourceId as
  // separate callback args; read WebContentsConsoleMessageEventParams from the event.
  mainWindow.webContents.on('console-message', (event) => {
    const { level, message, lineNumber, sourceId } =
      event as unknown as WebContentsConsoleMessageEventParams
    agentDebugLog('electron/main.ts:console-message', 'Renderer console message', {
      level,
      message,
      line: lineNumber,
      sourceId,
    }, 'A')
  })
  mainWindow.webContents.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL) => {
    agentDebugLog('electron/main.ts:did-fail-load', 'Renderer failed to load', {
      errorCode,
      errorDescription,
      validatedURL,
    }, 'C')
  })
  // #endregion

  await loadRenderer(mainWindow)
  sendWindowDisplayState()
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
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
