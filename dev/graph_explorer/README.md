# Developer Graph Explorer

Live visualization of the **active task subgraph** for debugging the engineering knowledge graph. This is a development-only tool — it does not ship with the desktop application UI.

## Architecture

```
Desktop App (unchanged)
       ↓ writes session state
sessions/*/tasks.json + standards/**/*_graph.db
       ↓ watched by
Graph Explorer dev server (:8765 REST + WebSocket)
       ↓ proxied by Vite
Browser UI (:3000 React + React Flow)
```

The explorer runs in a **separate process**. If it crashes, the desktop app continues normally.

## Prerequisites

- Python 3.12+ with project dependencies (`pip install -r requirements.txt`)
- Node.js 18+
- Graph databases built: `python scripts/build_all_standards_dbs.py`

## Quick start

### Terminal 1 — Desktop app

```bash
cd desktopApp
npm run dev
```

This starts the Python backend on port 8000 and the Electron app. Create or activate an engineering task (e.g. Pipe Wall Thickness).

### Terminal 2 — Graph explorer

```bash
cd dev/graph_explorer
pip install -r requirements.txt
npm run install:all
npm run dev
```

Open **http://localhost:3000** in your browser.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_ROOT` | repo root | Path to Ver03 project root |
| `GRAPH_EXPLORER_HOST` | `127.0.0.1` | Dev server bind address |
| `GRAPH_EXPLORER_PORT` | `8765` | Dev server port |
| `GRAPH_EXPLORER_SESSION` | `default` | Session / project id to read |
| `GRAPH_EXPLORER_AUTO_REBUILD` | `0` | Set to `1` to rebuild graph DB when node YAML changes |

## Live updates

The explorer watches:

- `sessions/<session>/tasks.json` — active task and `active_nodes` changes
- `standards/**/*_graph.db` — compiled graph changes after rebuild

When you edit node YAML sources, rebuild the graph database:

```bash
python scripts/build_graph_db.py
# or
python scripts/build_all_standards_dbs.py
```

With `GRAPH_EXPLORER_AUTO_REBUILD=1`, YAML edits trigger an automatic rebuild for the affected pack.

Updates are pushed over WebSocket (`/ws/graph`). If the WebSocket disconnects, the UI falls back to polling every 3 seconds.

## API endpoints (dev server :8765)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/api/graph/context` | Active task summary |
| GET | `/api/graph/snapshot` | Current subgraph |
| GET | `/api/graph/nodes/{id}` | Node detail |
| GET | `/api/graph/analysis` | Orphans, cycles, duplicates, etc. |
| GET | `/api/graph/search?q=` | Search nodes |
| WS | `/ws/graph` | Live snapshot/delta stream |

## Features

- React Flow canvas with zoom, pan, minimap, fit-to-screen, draggable nodes
- Dark theme
- Node type colors and edge type colors
- Search with viewport centering
- Filter by node type
- Side panel with ID, type, description, inputs, outputs, edges, metadata
- Graph analysis: orphans, no incoming/outgoing, cycles, duplicate names, disconnected components, highly connected nodes

## Tests

```bash
python -m pytest tests/dev
```

## Removal

Delete the `dev/graph_explorer/` directory. No production code imports this module.
