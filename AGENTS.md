# Engineering Desktop App — Agent Guide

Ver03 is a **Python engineering backend** plus an **Electron + React desktop client** (`desktopApp/`). The desktop app is a thin presentation layer; the backend owns calculations, standards, task state, and reports.

## Before coding

1. Read and follow `docs/rules.md` (workflow, verification, debugging, node structure).
2. Read the relevant doc under `docs/desktopApp/` (start with `14_desktop_app_implementation_roadmap.md`).
3. Inspect existing code in the target area (stores, `api/`, `desktopApp/src/`).
4. Propose a short plan for non-trivial changes (files, approach, risks).

## Architecture boundaries

| Layer | Owns |
| --- | --- |
| Backend (`api/`, `engine/`, `storage/`, `ai/`) | Engineering logic, validation, task state, SQLite, reports |
| Frontend (`desktopApp/src/`) | UI, Zustand stores, API client, rendering backend `task_state` |

Do **not** move engineering rules, formulas, or workflow logic into the frontend.

## Micro-graph data flow

Standards micro-graph nodes follow: **Markdown/YAML → GraphBuilder → PackGraph → SQLite cache**.

- Source of truth: `standards/*/nodes/**/node.{yaml,yml,md}`
- Runtime: `GraphStore` / `build_or_load_graph()` compile sources into a `PackGraph` in memory
- SQLite (`*_graph.db`) is an optional performance cache only; rebuild with `python scripts/build_graph_db.py`
- Canonical node types: `workflow`, `equation`, `parameter`, `text` — use `kind` metadata for variants (e.g. `parameter` + `kind: assumption`)

## Development order

Structure → data flow → backend connection → visualization → interaction → polish.

## Testing

- Backend: `python -m pytest tests/api tests/mvp/test_desktop_mvp_workflow.py`
- Frontend: `cd desktopApp && npm run test:run`
- MVP smoke: `cd desktopApp && npm run verify:mvp`
- Release gate: `cd desktopApp && npm run verify:release`
- After changing standards markdown/YAML: `python scripts/build_all_standards_dbs.py` then re-run backend tests

## Node Dev Studio (development only)

Isolated graph node CRUD UI for editing YAML sources under `standards/*/nodes/`.

1. Start backend with dev studio enabled:
   ```bash
   set DEV_STUDIO_ENABLED=1
   python -m api.server
   ```
2. Start the studio UI (browser only, no Electron):
   ```bash
   cd desktopApp && npm run dev:studio
   ```
3. Open `http://127.0.0.1:5173/studio.html`

The studio writes YAML and syncs `*_graph.db` incrementally. It is excluded from release builds (`npm run build` does not include `studio.html` unless `VITE_DEV_STUDIO=true`).

## Key paths

```
api/server.py              # Desktop REST API
desktopApp/electron/       # Main process, backend child process
desktopApp/src/store/      # Zustand state
desktopApp/src/services/api/  # Backend client
docs/desktopApp/           # Product and architecture docs
```

## After coding

Explain what changed, why, and any remaining risks. Keep diffs minimal and match existing conventions.
