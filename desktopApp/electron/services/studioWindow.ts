import { BrowserWindow } from 'electron'
import path from 'node:path'

import { normalizeDevServerUrl } from './devServer'

let studioWindow: BrowserWindow | null = null

export function closeStudioWindow(): void {
  if (!studioWindow) {
    return
  }
  if (!studioWindow.isDestroyed()) {
    studioWindow.close()
  }
  studioWindow = null
}

export async function openStudioWindow(isDev: boolean, devServerUrl?: string): Promise<void> {
  if (studioWindow && !studioWindow.isDestroyed()) {
    studioWindow.focus()
    return
  }

  studioWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'Node Dev Studio',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  studioWindow.on('closed', () => {
    studioWindow = null
  })

  if (isDev && devServerUrl) {
    const base = normalizeDevServerUrl(devServerUrl)
    await studioWindow.loadURL(`${base}/studio.html`)
    return
  }

  await studioWindow.loadFile(path.join(__dirname, '../dist/studio.html'))
}
