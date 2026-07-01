# electron — Architecture Audit

Electron **main process**: native shell, application menu, Python backend lifecycle, and IPC bridge to the renderer.

## Purpose

Runs outside the React renderer. Owns `BrowserWindow`, spawns and health-checks the Ver03 Python API server, writes desktop logs, and exposes a narrow `window.electronAPI` surface via preload.

## Files

| File | Purpose | Public API | Imports | Imported by |
| --- | --- | --- | --- | --- |
| `main.ts` | App bootstrap, window creation, IPC registration | `bootstrap` flow (implicit) | `menu`, `appLogger`, `backendProcess`, `devServer`, `startup`, `constants` | Vite electron plugin entry |
| `preload.ts` | Context-isolated IPC bridge | `window.electronAPI` | `constants` (types) | Loaded by `main.ts` webPreferences |
| `menu.ts` | Application menu | `createApplicationMenu` | `appLogger`, `constants` | `main.ts` |
| `services/startup.ts` | Resolve repo root, construct backend service | `runStartup`, `resolveRepoRoot` | `backendProcess`, `constants` | `main.ts` |
| `services/backendProcess.ts` | Spawn `python -m api.server`, poll `/health` | `BackendProcessService` | `constants`, `appLogger`, `pythonRuntime` | `startup.ts` |
| `services/pythonRuntime.ts` | Resolve Python executable path | `resolvePythonExecutable` | Node `fs`, `path` | `backendProcess.ts` |
| `services/devServer.ts` | Normalize Vite dev URL for Windows | `normalizeDevServerUrl` | — | `main.ts` |
| `services/appLogger.ts` | Append-only log file under userData | `initAppLogger`, `logAppEvent`, `getLogDirectory` | Node `fs`, `path` | `main.ts`, `menu.ts`, `backendProcess.ts` |

### Per-file detail

**`main.ts`**
- Inputs: Electron `app` lifecycle, env `VITE_DEV_SERVER_URL`
- Outputs: BrowserWindow, IPC events `backend:status`, `window:displayState`
- Side effects: spawns backend, quits on startup failure dialog
- Active: **High** — sole main-process entry

**`preload.ts`**
- Exposes: `getBackendStatus`, `retryBackendConnection`, `onBackendStatusChange`, `getWindowDisplayState`, `onWindowDisplayStateChange`, `platform`
- Side effects: IPC subscribe/unsubscribe
- Active: **High** — required for `useBackendConnection` and `useWindowDisplayState`

**`services/backendProcess.ts`**
- Sets `DEV_STUDIO_ENABLED=1` and `DEV_INSPECTION_ENABLED=1` when `enableDevStudio` (unpackaged)
- Polls `buildHealthUrl(backendUrl)` until timeout or connected
- Active: **High**

## Entry Points

| File | How entered |
| --- | --- |
| `main.ts` | `vite-plugin-electron` compiles to `dist-electron/main.js`; `package.json` `"main"` points here |
| Other files | Imported only from main process graph |

## Dependencies

**Depends on:**

- `../src/config/constants.ts` — shared backend URL, health path, status types (compiled into main bundle)
- Ver03 repo root (dev) or `resources/backend` (packaged) for Python cwd
- System or bundled `.venv` / embeddable Python

**Depended on by:**

- Renderer via `preload.ts` → `window.electronAPI` (typed in `src/types/frontend/electron.d.ts`)
- Tests: `tests/electron/pythonRuntime.test.ts`, `tests/electron/appLogger.test.ts`

## Runtime Usage

**Production:** Always runs when the desktop app launches.

**Development:** Same path; `loadRenderer` uses Vite dev server URL when `VITE_DEV_SERVER_URL` is set.

**Dev Studio (`npm run dev:studio`):** Electron plugin is **not** loaded (`vite.config.ts` `isStudioOnly`); this folder is **not** on that execution path.

## Possible Dead Code

| Item | Why | Confidence |
| --- | --- | --- |
| None identified | All 8 files are on the main-process import graph | High |

## Notes

- `resolveRepoRoot()`: packaged → `process.resourcesPath/backend`; dev → parent of `app.getAppPath()` (repo root).
- External links from renderer are denied in-window; `shell.openExternal` used instead (`main.ts` `setWindowOpenHandler`).
- Backend URL: `process.env.VITE_BACKEND_URL ?? constants.defaultBackendUrl` in `startup.ts` (main process env, not Vite `import.meta.env`).

## Execution Traces

### Cold start

```
electron/main.ts
  → initAppLogger(userData/logs)
  → createApplicationMenu
  → registerIpcHandlers (backend:getStatus, backend:retry, window:getDisplayState)
  → runStartup
      → new BackendProcessService(repoRoot, backendUrl, userData, !app.isPackaged)
      → backendProcess.start()
          → resolvePythonExecutable(repoRoot)
          → spawn(python, ['-m', 'api.server'], { env: BACKEND_HOST, BACKEND_PORT, ... })
          → poll fetch(buildHealthUrl) until ok or timeout
  → createWindow
      → preload.js
      → loadURL(Vite) | loadFile(dist/index.html)
  → sendBackendStatus → renderer onBackendStatusChange
```

### User retries backend (ConnectionErrorBanner)

```
Renderer: window.electronAPI.retryBackendConnection()
  → ipcMain.handle('backend:retry')
  → backendService.retry() → stop() → start()
  → sendBackendStatus
```

### Application quit

```
app.on('before-quit') → backendService.stop() → child.kill()
```
