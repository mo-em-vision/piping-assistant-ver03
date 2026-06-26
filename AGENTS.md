# Engineering Desktop App — Agent Guide

Ver03 is a **Python engineering backend** plus an **Electron + React desktop client** (`desktopApp/`). The desktop app is a thin presentation layer; the backend owns calculations, standards, task state, and reports.

## Before coding

1. Read the relevant doc under `docs/desktopApp/` (start with `14_desktop_app_implementation_roadmap.md`).
2. Inspect existing code in the target area (stores, `api/`, `desktopApp/src/`).
3. Propose a short plan for non-trivial changes (files, approach, risks).

## Architecture boundaries

| Layer | Owns |
| --- | --- |
| Backend (`api/`, `engine/`, `storage/`, `ai/`) | Engineering logic, validation, task state, SQLite, reports |
| Frontend (`desktopApp/src/`) | UI, Zustand stores, API client, rendering backend `task_state` |

Do **not** move engineering rules, formulas, or workflow logic into the frontend.

## Development order

Structure → data flow → backend connection → visualization → interaction → polish.

## Testing

- Backend: `python -m pytest tests/api tests/mvp/test_desktop_mvp_workflow.py`
- Frontend: `cd desktopApp && npm run test:run`
- MVP smoke: `cd desktopApp && npm run verify:mvp`
- Release gate: `cd desktopApp && npm run verify:release`
- After changing standards markdown/YAML: `python scripts/build_all_standards_dbs.py` then re-run backend tests

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
