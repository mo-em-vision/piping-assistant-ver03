# desktopApp — Architecture Audit

Electron + React + TypeScript presentation layer for the Ver03 engineering backend. The desktop client visualizes backend `task_state`, collects user input, and calls REST APIs; it does not own engineering calculations or standards logic.

Product architecture docs: [`docs/desktopApp/`](../docs/desktopApp/). This README documents the **current implementation** as of the audit.

## Purpose

Root package for the Engineering Workspace desktop application. Contains:

| Area | Path | Role |
| --- | --- | --- |
| Electron main process | `electron/` | Window, menu, Python backend child process, IPC |
| React renderer | `src/` | UI, Zustand stores, API client |
| Build / test | `vite.config.ts`, `vitest.config.ts`, `tests/` | Vite bundling, Vitest, Playwright |
| Packaging | `scripts/`, `electron-builder` config in `package.json` | Stage backend, NSIS installer |

## Files (top level)

| File / folder | Purpose |
| --- | --- |
| `package.json` | Dependencies, npm scripts (`dev`, `build`, `verify:mvp`, `package:win`) |
| `index.html` | Main app HTML shell → `src/main.tsx` |
| `vite.config.ts` | Vite + `vite-plugin-electron` |
| `vitest.config.ts` | Unit/integration test runner config |
| `tsconfig*.json` | TypeScript project references |
| `electron/` | Main process (see `electron/README.md`) |
| `src/` | Renderer source (see subfolder READMEs) |
| `tests/` | Vitest and Playwright tests |
| `scripts/` | `stage-backend.mjs`, `prepare-backend-venv.ps1` for packaging |
| `docs/README.md` | Developer setup guide (phases, env vars) — separate from this audit |
| `public/`, `build/`, `assets/` | Static assets and installer resources |

## Entry Points

| Entry | Trigger | File |
| --- | --- | --- |
| Electron main | `npm run dev` / packaged app | `electron/main.ts` → `dist-electron/main.js` |
| Main renderer | `index.html` | `src/main.tsx` → `App.tsx` |
| Preload bridge | Electron loads with window | `electron/preload.ts` → exposes `window.electronAPI` |

## Dependencies

**Outbound (this package depends on):**

- Ver03 Python backend (`python -m api.server`) spawned by Electron or run separately
- npm packages: React 19, Zustand, Vite, Electron, KaTeX, react-markdown

**Inbound (depends on this package):**

- End users (packaged installer)
- `dev/desktop_ui` (inspector, hovers, node edit tab)

## Runtime Usage

**Active in production path:** Yes. Packaged app runs `dist-electron/main.js`, loads `dist/index.html`, spawns bundled backend under `resources/backend`.

**Active in development:** `npm run dev` starts Vite on `127.0.0.1:5173` and Electron with `VITE_DEV_SERVER_URL`. Unpackaged Electron sets `DEV_INSPECTION_ENABLED=1` on the backend child process.

## Possible Dead Code

| Item | Evidence | Confidence |
| --- | --- | --- |
| `src/services/api/taskContinuationApi.ts` | Grep: only self-reference; no store/component imports | High |
| `src/types/backend/continuation.ts` | Only imported by `taskContinuationApi.ts` | High |
| `src/components/engineering/TaskProgress.tsx` | Grep: no imports outside its own file | High |
| `src/mock/*` when `VITE_MOCK_DATA` is not `true` | Used only in mock mode and tests | Medium (intentional test/dev path) |

## Notes

- `docs/README.md` lists product name "Engineering Knowledge Graph Assistant"; `constants.appName` matches. `package.json` `productName` is "Engineering Workspace".
- `VITE_MOCK_DATA=true` bypasses API calls in stores (`taskStore`, `projectStore`, `chatStore`, `reportStore`, `materialCatalogStore`).
- Path alias `@` → `src/` (configured in `vite.config.ts` and `tsconfig.json`).

## Execution Traces

### Application startup (packaged or `npm run dev`)

```
OS launches Electron
  → electron/main.ts (app.whenReady)
  → initAppLogger
  → bootstrap()
      → createApplicationMenu (electron/menu.ts)
      → registerIpcHandlers
      → runStartup (electron/services/startup.ts)
          → BackendProcessService.start() spawns python -m api.server
      → createWindow → loadRenderer (Vite URL or dist/index.html)
  → preload.ts exposes window.electronAPI
  → src/main.tsx → App.tsx
      → useBackendConnection (hooks/useBackend.ts) ← IPC backend:status
      → useWorkspaceBootstrap (hooks/useWorkspaceBootstrap.ts)
      → WorkspaceLayout (src/components/layout/WorkspaceLayout.tsx)
```

### Backend connected → workspace loaded

```
useWorkspaceBootstrap (backendStatus.status === 'connected')
  → connectionStore.checkApiConnection (GET /health)
  → materialCatalogStore.warmCatalog
  → projectStore.loadProjects
  → taskStore.loadRecentTasksGlobal
  → taskStore.loadWorkspace + chatStore.loadMessages (if active project)
```

### User submits workflow parameter

```
CenterPanel → WorkflowComposer → taskStore.submitParameter
  → inputApi.submit → POST /api/v1/tasks/{id}/inputs
  → taskStore.applyTaskState (updated TaskStateDto)
  → useActiveTaskViewModel → CenterPanel / RightPanel re-render
```

### User opens standards reference (right panel)

```
StandardReferenceLink / output link click
  → rightPanelStore.openReferenceTab
  → RightPanel renders NodeReferenceTab | TableReferenceTab
  → standardsApi.getNode | getTable
```

## Subfolder documentation

| README | Scope |
| --- | --- |
| [`electron/README.md`](electron/README.md) | Main process |
| [`src/services/api/README.md`](src/services/api/README.md) | REST client layer |
| [`src/store/README.md`](src/store/README.md) | Zustand stores |
| [`src/config/README.md`](src/config/README.md) | Env and constants |
| [`src/types/README.md`](src/types/README.md) | TypeScript contracts |
| [`src/components/README.md`](src/components/README.md) | UI components by subfolder |
