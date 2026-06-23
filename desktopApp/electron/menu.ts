import { app, BrowserWindow, Menu, dialog, shell } from 'electron'

import { constants } from '../src/config/constants'

export function createApplicationMenu(getMainWindow: () => BrowserWindow | null): void {
  const isMac = process.platform === 'darwin'

  const template: Electron.MenuItemConstructorOptions[] = [
    ...(isMac
      ? [
          {
            label: app.name,
            submenu: [
              {
                label: `About ${constants.appName}`,
                click: () => {
                  void dialog.showMessageBox({
                    type: 'info',
                    title: 'About',
                    message: constants.appName,
                    detail: `Version ${app.getVersion()}\nEngineering workspace desktop client.`,
                  })
                },
              },
              { type: 'separator' as const },
              { role: 'services' as const },
              { type: 'separator' as const },
              { role: 'hide' as const },
              { role: 'hideOthers' as const },
              { role: 'unhide' as const },
              { type: 'separator' as const },
              { role: 'quit' as const },
            ],
          },
        ]
      : []),
    {
      label: 'File',
      submenu: [
        {
          label: 'Reload',
          accelerator: 'CmdOrCtrl+R',
          click: () => {
            getMainWindow()?.webContents.reload()
          },
        },
        { type: 'separator' },
        isMac ? { role: 'close' as const } : { role: 'quit' as const },
      ],
    },
    { role: 'editMenu' },
    {
      label: 'View',
      submenu: [
        { role: 'resetZoom' as const },
        { role: 'zoomIn' as const },
        { role: 'zoomOut' as const },
        { type: 'separator' },
        {
          label: 'Toggle Developer Tools',
          accelerator: 'F12',
          click: () => {
            getMainWindow()?.webContents.toggleDevTools()
          },
        },
        { role: 'togglefullscreen' as const },
      ],
    },
    {
      label: 'Help',
      submenu: [
        ...(!isMac
          ? [
              {
                label: `About ${constants.appName}`,
                click: () => {
                  void dialog.showMessageBox({
                    type: 'info',
                    title: 'About',
                    message: constants.appName,
                    detail: `Version ${app.getVersion()}\nEngineering workspace desktop client.`,
                  })
                },
              },
            ]
          : []),
        {
          label: 'Open Project Repository',
          click: () => {
            void shell.openExternal('https://github.com/mo-em-vision/piping-assistant-ver03')
          },
        },
      ],
    },
  ]

  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}
