# Developer Graph Explorer — Architecture Audit

Audit date: 2026-07-01. Documentation reflects the code as it exists today; no architectural recommendations.

**User guide (quick start, features):** [`docs/developer_graph_explorer.md`](../../docs/developer_graph_explorer.md)

---

## Purpose

Live visualization of the **active task subgraph** for debugging the engineering knowledge graph. A **development-only** tool: separate Python (Starlette) + Vite/React processes; does not ship with the desktop application UI.

Responsibilities:

- Read active task context and `active_nodes` from the same session storage as the desktop API
- Load node/edge metadata from per-pack `*_graph.db` via `GraphStore` (read-only)
- Build an **induced subgraph** (edges only when both endpoints are in `active_nodes`)
- Serve REST + WebSocket API on `:8765`; browser UI on `:3000` via Vite proxy
- Watch `tasks.json` and graph DB / YAML sources; push snapshot or delta updates to clients
- Run graph analysis (orphans, cycles, duplicates, components, hubs) on the current subgraph

The explorer **does not modify** graph sources or task state.

---

## Files

### Python (package root)

| File | Role |
|------|------|
| `__init__.py` | Package docstring only. |
| `__main__.py` | CLI entry: uvicorn on `GRAPH_EXPLORER_HOST` / `GRAPH_EXPLORER_PORT`. |
| `server.py` | Starlette app: REST routes, WebSocket, `GraphExplorerService`, lifespan watcher. |
| `adapter.py` | `TaskContextReader`, `GraphExplorerAdapter`, `GraphViewProvider` protocol. |
| `explorer_config.py` | Desktop user-data resolution, session auto-pick, `debug_log`. |
| `serializer.py` | JSON-serializable DTOs for API responses. |
| `analysis.py` | `analyze_graph` — structural analysis of node/edge lists. |
| `delta.py` | `compute_delta` — diff snapshots for WebSocket incremental updates. |
| `watcher.py` | `watchdog` observer on standards + session `tasks.json`; optional YAML auto-rebuild. |
| `requirements.txt` | Dev-only: `starlette`, `uvicorn`, `watchdog`. |

### Node / tooling

| File | Role |
|------|------|
| `package.json` | `npm run dev` runs server + web via `concurrently`; `predev` frees ports. |
| `package-lock.json` | Lockfile for root npm deps. |
| `scripts/run-dev-server.mjs` | Spawns `python -m dev.graph_explorer` with `PROJECT_ROOT` / `PYTHONPATH`. |
| `scripts/free-dev-ports.mjs` | Kills processes on ports 3000 and 8765 (Windows + Unix). |
| `scripts/free-port.mjs` | Backward-compat wrapper calling `free-dev-ports.mjs` (not wired to npm scripts). |

### Web (`web/`)

| File | Role |
|------|------|
| `index.html` | Vite HTML shell. |
| `package.json` | React 18, `@xyflow/react`, `dagre`, `zustand`, Vite 6. |
| `vite.config.ts` | Port 3000; proxies `/api`, `/ws`, `/health` → `127.0.0.1:8765`. |
| `tsconfig.json` | TypeScript project config. |
| `src/main.tsx` | React root mount. |
| `src/App.tsx` | Layout: header, sidebar (search/filter/analysis), canvas, side panel. |
| `src/types.ts` | TS interfaces mirroring API DTOs. |
| `src/hooks/useGraphWebSocket.ts` | WebSocket + 3s polling fallback; REST helpers. |
| `src/store/graphStore.ts` | Zustand: snapshot/delta, layout positions, filters, React Flow nodes/edges. |
| `src/components/GraphCanvas.tsx` | React Flow canvas, minimap, empty-state message. |
| `src/components/GraphNode.tsx` | Custom node renderer (type colors, execution state). |
| `src/components/GraphEdge.tsx` | Custom edge renderer (type color, traversed animation). |
| `src/components/SearchBar.tsx` | Client search + server `/api/graph/search` (via store filtering). |
| `src/components/FilterBar.tsx` | Toggle visibility by node type. |
| `src/components/AnalysisPanel.tsx` | Displays `analyze_graph` results. |
| `src/components/SidePanel.tsx` | Node detail from `/api/graph/nodes/{id}`. |
| `src/components/Toolbar.tsx` | Fit view, zoom controls. |
| `src/utils/layout.ts` | Dagre top-to-bottom layout for flow nodes. |
| `src/utils/nodeStyles.ts` | Node/edge color maps by type and `kind`. |
| `src/theme/dark.css` | App shell and component styles. |
| `src/vite-env.d.ts` | Vite client types. |

---

## Entry Points

| Entry | How it is reached |
|-------|-------------------|
| `python -m dev.graph_explorer` | `__main__.py` → `create_app()` → `uvicorn.run`. |
| `npm run dev` | `package.json`: `predev` → `free-dev-ports.mjs`; `dev:server` + `dev:web`. |
| `npm run dev:server` | `run-dev-server.mjs` only. |
| `npm run dev:web` | `vite` in `web/`. |
| `create_app(project_root)` | Imported by `__main__.py`; usable from tests (no dedicated test imports found). |

Library modules (`adapter`, `analysis`, `serializer`, etc.) are imported by `server.py`, each other, and `tests/dev/`.

---

## Dependencies

### This package depends on

| Area | Modules |
|------|---------|
| **Config** | `config.loader.CLIConfig` |
| **Engine** | `engine.graph.graph_store.GraphStore`, `engine.graph.graph_engine.normalize_root_id`, `engine.reference.graph_db`, `engine.reference.standards_paths.list_standard_packs`, `engine.state.state_manager.TaskStateManager` |
| **Storage** | `storage.migrate_legacy_sessions`, `storage.project_repository.ProjectRepository`, `storage.project_session_store.ProjectSessionStore`, `get_database_for_config` |
| **Models** | `models.task.Task` |
| **Scripts** | `scripts.build_graph_db.build_pack_graph_db` (lazy import in `watcher.py` when auto-rebuild enabled) |
| **Python third-party** | `starlette`, `uvicorn`, `watchdog` |
| **Frontend** | `react`, `@xyflow/react`, `dagre`, `zustand`, `vite` |

### Who depends on this package

Grep `from dev.graph_explorer` / `dev/graph_explorer` / `python -m dev.graph_explorer` (2026-07-01):

| Importer | Imports |
|----------|---------|
| `dev/graph_explorer/__main__.py` | `server.create_app` |
| `dev/graph_explorer/server.py` | `explorer_config`, `adapter`, `analysis`, `delta`, `serializer`, `watcher` |
| `dev/graph_explorer/adapter.py` | `explorer_config.debug_log`, `serializer.*` |
| `dev/graph_explorer/analysis.py` | `serializer.GraphEdgeDto`, `GraphNodeDto` |
| `dev/graph_explorer/delta.py` | `serializer.*` |
| `tests/dev/test_graph_explorer_adapter.py` | `GraphExplorerAdapter`, `TaskContextReader`, DTOs |
| `tests/dev/test_graph_explorer_analysis.py` | `analyze_graph`, DTOs |
| `dev/graph_explorer/scripts/run-dev-server.mjs` | Spawns module (no Python import) |

**Not imported by:** `api/`, `cli/`, `engine/` (except graph_explorer calling engine APIs), `desktopApp/` production bundles.

---

## Runtime Usage

**Dev-only execution path.** Not loaded by `api/server.py` or Electron release builds.

### How you know

- Started only via `python -m dev.graph_explorer` or `npm run dev` in this directory.
- Binds `127.0.0.1:8765` (API) and `localhost:3000` (UI) by default.
- Reads `CLIConfig.sessions_dir`, `CLIConfig.standards_root`, and `desktop.db` project list — same config loader as CLI/API.
- Writes only optional `debug-b5dce6.log` at repo root (debug instrumentation).

### Verification

```bash
python -m pytest tests/dev -q
cd dev/graph_explorer && npm run dev   # manual smoke (not run during audit)
```

---

## Possible Dead Code

| Item | Why it appears unused | Confidence |
|------|------------------------|------------|
| `GraphViewProvider` (`adapter.py`) | Protocol defined; `GraphExplorerService` uses `GraphExplorerAdapter` directly with no alternate implementations. | High |
| `resolve_workflow_node_id` import (`adapter.py`) | Imported from `engine.graph.graph_engine` but never referenced in file. | High |
| `fetchContext()` (`useGraphWebSocket.ts`) | Exported; no callers in repo (grep). | High |
| `scripts/free-port.mjs` | Not referenced by `package.json` or other scripts. | High |
| `web/package.json` `"graph-explorer": "file:.."` | Parent package has no runtime exports used by web; likely unused dependency entry. | Medium |

Do not delete based on audit alone.

---

## Notes

- **Agent debug logging:** `__main__.py`, `explorer_config.debug_log`, `run-dev-server.mjs`, `free-dev-ports.mjs`, `vite.config.ts`, and `useGraphWebSocket.ts` contain `#region agent log` blocks writing `debug-b5dce6.log` and/or POSTing to `http://127.0.0.1:7445/ingest/...`. Unusual for production tooling; purpose unknown from static analysis beyond debug session `b5dce6`.
- **Execution overlay:** `adapter._execution_states_from_task` maps `task.outputs._execution_trace` into node `metadata.execution_state` and edge `metadata.traversed` — integrates with Developer Inspection Framework trace data when present.
- **Unknown nodes:** Active node IDs missing from graph DB get `node_type: "unknown"` placeholders in the subgraph.
- **WebSocket keepalive:** Server loop `receive_text()` on `/ws/graph`; client does not send messages — disconnect handling only.
- **Delta vs layout:** `applyDelta` in `graphStore.ts` updates positions incrementally; full `setSnapshot` re-runs dagre layout.

---

## Duplicate Implementations

| Concern | This package | Elsewhere |
|---------|--------------|-----------|
| Task subgraph visualization | Browser React Flow, induced `active_nodes` subgraph | `desktopApp/.../inspector/InspectorGraphPanel.tsx` |
| Graph structure CLI view | Not implemented (protocol only) | `cli/commands/graph.py` |
| Graph DB build | Optional watcher → `build_pack_graph_db` | `scripts/build_graph_db.py`, `scripts/build_all_standards_dbs.py` |
| Session/task read path | `TaskContextReader` via `ProjectSessionStore` | `api/desktop_service.py`, `cli/session_store.py` |

---

## Execution Traces

### A. Startup (`npm run dev`)

```text
dev/graph_explorer/package.json → predev
    ↓
scripts/free-dev-ports.mjs (ports 3000, 8765)
    ↓
concurrently
    ├── dev:server → scripts/run-dev-server.mjs
    │       ↓ spawn python -m dev.graph_explorer (cwd=repo root, PYTHONPATH=repo root)
    │       ↓
    │   __main__.py → create_app(project_root)
    │       ↓
    │   server.create_app
    │       ├── explorer_config.apply_desktop_user_data_env
    │       ├── CLIConfig.load
    │       ├── explorer_config.resolve_session_id
    │       ├── GraphExplorerAdapter(config, session_id)
    │       └── GraphExplorerService(adapter)
    │       ↓
    │   lifespan on_startup
    │       ├── service.set_loop
    │       ├── GraphWatcher.start (standards + sessions/<id>/tasks.json)
    │       └── service._refresh_and_broadcast
    │
    └── dev:web → vite (web/)
            ↓ proxy /api, /ws → :8765
```

### B. HTTP GET `/api/graph/snapshot`

```text
server.graph_snapshot
    ↓
GraphExplorerService._lock
    ↓ (if _snapshot is None)
adapter.reload() → _reload_stores() → GraphStore.load per pack
adapter.get_snapshot()
    ↓
TaskContextReader.read() → ProjectSessionStore → TaskStateManager
    ↓
_build_subgraph(active_nodes, execution_states)
    ↓
JSONResponse(snapshot.to_dict())
```

### C. Filesystem change → WebSocket push

```text
watchdog GraphChangeHandler.on_any_event
    ↓ (optional) _maybe_rebuild_pack → scripts.build_graph_db.build_pack_graph_db
    ↓
_schedule_notify (350ms debounce)
    ↓
GraphExplorerService._refresh_and_broadcast
    ↓
adapter.reload(); snapshot = adapter.get_snapshot()
delta = compute_delta(previous, snapshot)
    ↓
asyncio.run_coroutine_threadsafe → _broadcast
    ↓
WebSocket send_json({type: snapshot|delta, ...})
    ↓
web/useGraphWebSocket → graphStore.setSnapshot | applyDelta
    ↓
GraphCanvas (React Flow render)
```

### D. User selects node in UI

```text
App.selectNode
    ↓
fetchNodeDetail → GET /api/graph/nodes/{id}
    ↓
server.graph_node → adapter.get_node
    ↓
GraphStore incoming/outgoing + metadata → NodeDetailDto
    ↓
SidePanel renders detail; focusNode centers viewport
```

### E. Graph analysis panel refresh

```text
App useEffect on revision
    ↓
fetchAnalysis → GET /api/graph/analysis
    ↓
server.graph_analysis → analyze_graph(snapshot.nodes, snapshot.edges)
    ↓
AnalysisPanel displays report
```

---

## Per-File Inventory

### `__main__.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Process entry for uvicorn. |
| **Public API** | `main()` |
| **Inputs** | Env: `PROJECT_ROOT`, `GRAPH_EXPLORER_HOST`, `GRAPH_EXPLORER_PORT` |
| **Outputs** | Runs HTTP server until killed |
| **Side effects** | Binds TCP port; optional append to `debug-b5dce6.log` |
| **Imported by** | `python -m` execution only |
| **Imports** | `uvicorn`, `dev.graph_explorer.server.create_app` |
| **Actively used** | Yes |
| **Confidence** | High |

### `server.py`

| Field | Detail |
|-------|--------|
| **Purpose** | HTTP/WebSocket surface and service orchestration. |
| **Public API** | `create_app`, `GraphExplorerService`, `on_startup`, `on_shutdown` |
| **Inputs** | `project_root`, HTTP/WS requests |
| **Outputs** | JSON responses, WebSocket messages |
| **Side effects** | Starts `GraphWatcher`; holds in-memory snapshot cache |
| **Imported by** | `__main__.py` |
| **Imports** | `config.loader`, all sibling graph_explorer modules, `starlette` |
| **Actively used** | Yes |
| **Confidence** | High |

### `adapter.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Bridge session state + `GraphStore` → DTO snapshots. |
| **Public API** | `TaskContext`, `TaskContextReader`, `GraphExplorerAdapter`, `GraphViewProvider` |
| **Inputs** | `CLIConfig`, `session_id`; active_nodes from task state |
| **Outputs** | `GraphContextDto`, `GraphSnapshotDto`, `NodeDetailDto`, search results |
| **Side effects** | Reads SQLite graph DBs and session DB; `debug_log` |
| **Imported by** | `server.py`, `tests/dev/test_graph_explorer_adapter.py` |
| **Imports** | `config`, `engine.*`, `models.task`, `storage.*`, `serializer`, `explorer_config` |
| **Actively used** | Yes (`GraphViewProvider` itself unused as polymorphic type) |
| **Confidence** | High |

### `explorer_config.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Align explorer with desktop user-data and project selection. |
| **Public API** | `resolve_desktop_user_data`, `apply_desktop_user_data_env`, `resolve_session_id`, `debug_log` |
| **Inputs** | `CLIConfig`, env vars, `ProjectRepository.list_projects` |
| **Outputs** | Session id string; may set `DESKTOP_USER_DATA` |
| **Side effects** | `os.environ.setdefault`; debug log file |
| **Imported by** | `server.py`, `adapter.py` (debug_log only) |
| **Imports** | `config.loader`, `storage.project_repository`, `storage.project_session_store` |
| **Actively used** | Yes |
| **Confidence** | High |

### `serializer.py`

| Field | Detail |
|-------|--------|
| **Purpose** | API DTOs with `to_dict()`. |
| **Public API** | `GraphEdgeDto`, `GraphNodeDto`, `GraphContextDto`, `GraphSnapshotDto`, `EdgeRefDto`, `NodeDetailDto` |
| **Inputs** | Constructor fields |
| **Outputs** | `dict` for JSON serialization |
| **Side effects** | None |
| **Imported by** | `adapter`, `analysis`, `delta`, `server`, tests |
| **Imports** | stdlib `dataclasses` only |
| **Actively used** | Yes |
| **Confidence** | High |

### `analysis.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Structural diagnostics on a node/edge list. |
| **Public API** | `analyze_graph`, `GraphAnalysisReport` |
| **Inputs** | `list[GraphNodeDto]`, `list[GraphEdgeDto]`, optional `hub_threshold` |
| **Outputs** | `GraphAnalysisReport` |
| **Side effects** | None |
| **Imported by** | `server.py`, `tests/dev/test_graph_explorer_analysis.py` |
| **Imports** | `serializer` |
| **Actively used** | Yes |
| **Confidence** | High |

### `delta.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Diff two snapshots for incremental WS updates. |
| **Public API** | `compute_delta`, `GraphDelta` |
| **Inputs** | Previous and current `GraphSnapshotDto` |
| **Outputs** | `GraphDelta` or `None` if unchanged revision |
| **Side effects** | None |
| **Imported by** | `server.py` |
| **Imports** | `serializer` |
| **Actively used** | Yes |
| **Confidence** | High |

### `watcher.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Filesystem notifications for live refresh. |
| **Public API** | `GraphWatcher`, `GraphChangeHandler`, `auto_rebuild_enabled` |
| **Inputs** | `standards_root`, `sessions_dir`, `session_id`, `on_change` callback |
| **Outputs** | Invokes `on_change` after debounce |
| **Side effects** | `watchdog` observer threads; may rebuild pack SQLite |
| **Imported by** | `server.py` |
| **Imports** | `watchdog`; lazy `scripts.build_graph_db` |
| **Actively used** | Yes |
| **Confidence** | High |

### `web/src/hooks/useGraphWebSocket.ts`

| Field | Detail |
|-------|--------|
| **Purpose** | Real-time graph sync and REST helpers. |
| **Public API** | `useGraphWebSocket`, `fetchNodeDetail`, `fetchAnalysis`, `fetchContext` |
| **Inputs** | WebSocket messages; HTTP responses |
| **Outputs** | Updates `graphStore` |
| **Side effects** | WebSocket connection; polling interval; debug POSTs |
| **Imported by** | `App.tsx` (`useGraphWebSocket`, `fetchNodeDetail`, `fetchAnalysis`) |
| **Imports** | `graphStore`, `types` |
| **Actively used** | Yes (`fetchContext` unused) |
| **Confidence** | High |

### `web/src/store/graphStore.ts`

| Field | Detail |
|-------|--------|
| **Purpose** | Client state: raw graph, React Flow projection, UI filters. |
| **Public API** | `useGraphStore` hook and actions |
| **Inputs** | Snapshot/delta payloads, user interactions |
| **Outputs** | `flowNodes`, `flowEdges` for canvas |
| **Side effects** | Dagre layout on full snapshot |
| **Imported by** | `App.tsx`, components, `useGraphWebSocket.ts` |
| **Imports** | `zustand`, `@xyflow/react`, `layout`, `nodeStyles`, `types` |
| **Actively used** | Yes |
| **Confidence** | High |

---

## Quick Start (summary)

Full steps: [`docs/developer_graph_explorer.md`](../../docs/developer_graph_explorer.md).

```bash
# Terminal 1 — desktop app with active task
cd desktopApp && npm run dev

# Terminal 2 — graph explorer
cd dev/graph_explorer
pip install -r requirements.txt
npm run install:all
npm run dev
```

Open **http://localhost:3000**. API on **http://127.0.0.1:8765**.

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_ROOT` | repo root | Ver03 root path |
| `GRAPH_EXPLORER_HOST` | `127.0.0.1` | API bind address |
| `GRAPH_EXPLORER_PORT` | `8765` | API port |
| `GRAPH_EXPLORER_SESSION` | `auto` | Project id or auto-pick active desktop project |
| `GRAPH_EXPLORER_AUTO_REBUILD` | `0` | `1` to rebuild graph DB on YAML change |

## API (dev server :8765)

| Method | Path | Handler |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/api/graph/context` | Task summary |
| GET | `/api/graph/snapshot` | Subgraph (`?revision=` for 304-style unchanged) |
| GET | `/api/graph/nodes/{id}` | Node detail |
| GET | `/api/graph/analysis` | Structural analysis |
| GET | `/api/graph/search?q=` | Subgraph search |
| WS | `/ws/graph` | Snapshot + delta stream |

## Tests

```bash
python -m pytest tests/dev -q
```

## Removal

Delete `dev/graph_explorer/`. No production code imports this module.
