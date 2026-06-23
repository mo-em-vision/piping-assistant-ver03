# Desktop Application

Electron + React + TypeScript frontend for the Engineering Knowledge Graph Assistant.

Architecture documentation lives in the repository root at [`docs/desktopApp/`](../docs/desktopApp/).

## Prerequisites

- Node.js 20+
- npm 10+

## Setup

```bash
cd desktopApp
npm install
cp .env.example .env   # Windows: copy .env.example .env
```

## Development

```bash
npm run dev
```

Starts the Vite dev server and opens the Electron window.

## Build

```bash
npm run build
```

Produces renderer assets in `dist/` and Electron main/preload bundles in `dist-electron/`.

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `VITE_BACKEND_URL` | Backend API base URL (Phase 3+) | `http://localhost:8000` |
| `VITE_APP_NAME` | Window and UI title | Engineering Knowledge Graph Assistant |
| `VITE_DEV_MODE` | Enable developer diagnostics | `true` in development |

See [`.env.example`](.env.example) for the full list.

## Project structure

```
desktopApp/
├── electron/          # Main process, preload, native services
├── src/               # React renderer
├── public/            # Static assets
├── assets/            # Icons and images
├── tests/             # Frontend tests (Phase 11+)
└── docs/              # Desktop-app-specific notes
```

Implementation follows [`14_desktop_app_implementation_roadmap.md`](../docs/desktopApp/14_desktop_app_implementation_roadmap.md).

## Phases

| Phase | Status |
| --- | --- |
| 0 — Project initialization | Complete |
| 1 — Desktop shell (menu, startup, backend) | Complete |
| 2 — Main layout (three-panel workspace) | Complete |
| 3 — Backend connection layer | Complete |
| 4 — State visualization | Complete |
| 5 — Input system | Complete |
| 6 — Output rendering engine | Complete |
| 7 — AI chat interface | Complete |
| 8 — Project and task storage | Complete |
| 9 — Report integration | Complete |
| 10 — Error handling | Complete |
| 11 — Testing integration | Complete |
| 12 — Packaging | Complete |
| 13 — MVP verification | Complete |
| 14 — Cursor implementation rules | Complete |
| 15 — MVP completion & release readiness | Complete |

## MVP verification

```bash
npm run verify:mvp
```

Runs frontend workflow tests and backend MVP contract tests (`tests/mvp/test_desktop_mvp_workflow.py`).

## Release verification

```bash
npm run verify:release
```

Runs typecheck, MVP smoke tests, and release readiness checks before packaging.

## Packaging

```bash
npm run package:win
```

See Phase 12 in the implementation roadmap for details.
