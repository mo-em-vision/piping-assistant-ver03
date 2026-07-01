# dev/ — Architecture Audit

Audit date: 2026-07-01. Documentation reflects the code as it exists today; no architectural recommendations.

---

## Purpose

The `dev/` package is the **Python namespace for development-only tooling** that is not part of the production desktop application build or the main REST API (`api/server.py`). Tools here run as **separate processes** during local development and may read the same session storage and compiled graph databases as the desktop app, but they do not ship in release builds and are not imported by production backend routes.

Today the folder contains a single substantive tool: **Developer Graph Explorer** (`dev/graph_explorer/`). The root `__init__.py` only documents that intent.

**Related but out of scope for this folder:** inline dev UI under `desktopApp/src/components/dev/` (Developer Inspector, Node Dev Studio tab, dev hovers) lives in the Electron app, not under `dev/`.

---

## Files

| Path | Role |
|------|------|
| `__init__.py` | Package docstring: development-only tools, not production. |
| `graph_explorer/` | Live React Flow visualization of the active task subgraph. **Full audit:** [`graph_explorer/README.md`](graph_explorer/README.md). |

No other subpackages or modules exist under `dev/` at audit time.

---

## Entry Points

| Entry | How it is reached |
|-------|-------------------|
| `python -m dev.graph_explorer` | `dev/graph_explorer/__main__.py` → uvicorn + Starlette on `:8765`. |
| `npm run dev` (in `dev/graph_explorer/`) | `predev` frees ports 3000/8765; `concurrently` runs Python server + Vite (`:3000`). |
| `from dev.graph_explorer import …` | Used by tests (`tests/dev/`) and internal graph_explorer modules only. |

`dev/__init__.py` is **not** an executable entry point.

---

## Dependencies

### This folder depends on

| Area | Consumers under `dev/` |
|------|------------------------|
| **Config** | `config.loader.CLIConfig` (`graph_explorer/server.py`, `adapter.py`, `explorer_config.py`) |
| **Engine** | `engine.graph.graph_store`, `engine.graph.graph_engine`, `engine.reference.*`, `engine.state.state_manager` (`graph_explorer/adapter.py`) |
| **Storage** | `storage.project_repository`, `storage.project_session_store`, `storage.migrate_legacy_sessions` (`graph_explorer/adapter.py`, `explorer_config.py`) |
| **Models** | `models.task.Task` (`graph_explorer/adapter.py`) |
| **Scripts** | `scripts.build_graph_db.build_pack_graph_db` (optional auto-rebuild in `graph_explorer/watcher.py`) |
| **Dev Python packages** | `starlette`, `uvicorn`, `watchdog` (`graph_explorer/requirements.txt`) |
| **Dev Node packages** | `concurrently` (root `graph_explorer/package.json`); React/Vite stack in `graph_explorer/web/` |

### Who depends on this folder

Grep for `from dev.` / `import dev` / `dev.graph_explorer` / `dev/graph_explorer` (2026-07-01):

| Consumer | Relationship |
|----------|--------------|
| `tests/dev/test_graph_explorer_adapter.py` | Imports `GraphExplorerAdapter`, `TaskContextReader`, DTOs. |
| `tests/dev/test_graph_explorer_analysis.py` | Imports `analyze_graph`, DTOs. |
| `dev/graph_explorer/scripts/run-dev-server.mjs` | Spawns `python -m dev.graph_explorer`. |
| Internal `dev/graph_explorer/*.py` | Package-internal imports only. |

**No imports from:** `api/`, `engine/` (except tests), `desktopApp/` production code, `cli/`, `storage/` (except graph_explorer reading storage APIs).

Docs referencing `dev/` (not runtime imports): `AGENTS.md`, `docs/developer_graph_explorer.md`, `docs/developer_inspection_framework.md`, `docs/node_dev_studio.md`, `config/README.md`, `models/README.md`, `storage/README.md`, `scripts/README.md`.

---

## Runtime Usage

**Not on the production desktop or API execution path.** Active only when a developer explicitly starts Graph Explorer.

### Proof (static analysis, 2026-07-01)

- `api/server.py` does not import `dev`.
- `desktopApp/electron/` and release `npm run build` do not bundle `dev/graph_explorer/web`.
- `.gitignore` excludes `dev/graph_explorer/**/node_modules/`.
- Graph Explorer reads session state written by the desktop backend; it does not write task state.

### Typical developer flow

```text
desktopApp npm run dev  (or python -m api.server)
    ↓
sessions/<project>/tasks.json updated with active_nodes
standards/**/*_graph.db compiled
    ↓
cd dev/graph_explorer && npm run dev
    ↓
run-dev-server.mjs → python -m dev.graph_explorer (:8765)
Vite dev server (:3000) proxies /api, /ws, /health → :8765
    ↓
Browser React UI ← WebSocket /ws/graph + REST
```

See [`graph_explorer/README.md`](graph_explorer/README.md) for module-level traces and per-file inventory.

---

## Possible Dead Code

| Item | Why it appears unused | Confidence |
|------|------------------------|------------|
| `dev/__init__.py` | Empty aside from docstring; no re-exports. | High |
| `dev/graph_explorer/scripts/free-port.mjs` | Wraps `free-dev-ports.mjs` but not referenced by `package.json` or other scripts. | High |
| See [`graph_explorer/README.md`](graph_explorer/README.md) | Additional dead-code notes inside graph_explorer (e.g. `GraphViewProvider`, unused imports). | — |

---

## Notes

- **Isolation:** Graph Explorer failure does not stop the desktop app (separate process, separate ports).
- **Session alignment:** `explorer_config.resolve_session_id` and `apply_desktop_user_data_env` mirror Electron user-data paths so the explorer reads the same `desktop.db` / sessions as the running app when `GRAPH_EXPLORER_SESSION=auto`.
- **Debug instrumentation:** Multiple graph_explorer files append to repo-root `debug-b5dce6.log` and (in the web hook) POST to a local ingest URL — appears to be temporary agent/debug tracing, not product behavior.
- **Documentation split:** User guide lives in [`docs/developer_graph_explorer.md`](../docs/developer_graph_explorer.md); this audit and [`graph_explorer/README.md`](graph_explorer/README.md) document implementation as-is.

---

## Duplicate Implementations

| Capability | `dev/graph_explorer` | Other location |
|------------|----------------------|----------------|
| Active subgraph visualization | React Flow browser UI, induced subgraph from `active_nodes` | `desktopApp/src/components/dev/inspector/InspectorGraphPanel.tsx` (in-app, inspection payload) |
| Full / CLI graph view | Not implemented (`GraphViewProvider` protocol only) | `cli/commands/graph.py` — `graph show` dependency tree from standards packs |
| Node authoring | Read-only | Node Dev Studio (`docs/node_dev_studio.md`) — writes YAML |

No recommendation on which to keep; documented for navigation only.

---

## Child folder status

| Folder | README | Audit status |
|--------|--------|--------------|
| `graph_explorer/` | [`graph_explorer/README.md`](graph_explorer/README.md) | Complete (2026-07-01) |
