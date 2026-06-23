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
