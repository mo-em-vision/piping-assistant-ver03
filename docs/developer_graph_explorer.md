# Developer Graph Explorer

Development-only tool for live visualization of the **active task subgraph** in the engineering knowledge graph. It is not part of the desktop application UI and does not ship in release builds.

**Quick start:** see [`dev/graph_explorer/README.md`](../dev/graph_explorer/README.md).

---

## 1. Purpose

The Graph Explorer helps developers and AI-assisted workflows debug graph structure while the desktop app is running:

- See which nodes are active for the current task (`Task.active_nodes`)
- Inspect relationships (edges) between those nodes
- Search, filter, and analyze subgraph health (orphans, cycles, duplicates, etc.)
- Receive live updates when session state or compiled graph databases change

The explorer **never modifies** graph data. It reads session state and compiled graph SQLite databases through a thin adapter.

---

## 2. Isolation from production

| Property | Behavior |
|----------|----------|
| Process | Separate Python + Vite processes (`dev/graph_explorer/`) |
| Ports | API `:8765`, browser UI `:3000` (not `:8000` / `:5173`) |
| Desktop UI | No changes to `desktopApp/` |
| Main API | No routes added to `api/server.py` |
| Crash safety | Explorer crash does not affect the desktop app |
| Removal | Delete `dev/graph_explorer/` — no production imports |

---

## 3. Architecture

```
Desktop App (Electron + React)
       │
       ▼
api.server (:8000)  ──writes──▶  sessions/<id>/tasks.json
       │                                    │
       │                                    │ active_nodes, task outputs
       ▼                                    ▼
standards/**/*_graph.db  ◀──build──  node YAML sources
       │
       │  file watcher
       ▼
dev.graph_explorer server (:8765)
  ├── GraphExplorerAdapter  →  GraphStore (read-only)
  ├── REST API
  └── WebSocket /ws/graph
       │
       ▼  Vite proxy
Browser (:3000)  React + @xyflow/react
```

### Data scope

The explorer shows the **induced subgraph** for the active desktop task:

1. Read `active_task_id` and `Task.active_nodes` from session storage (same path as the desktop API).
2. Load node metadata and edges from per-pack `*_graph.db` via `GraphStore`.
3. Include only edges where **both** endpoints are in `active_nodes`.

It does **not** load the full standards corpus (5k–10k nodes) by default. A `GraphViewProvider` protocol in the adapter allows future modes (full pack, dependency trace, impact analysis).

### Live updates

Graph sources are compile-time (YAML → SQLite). Runtime changes appear when:

| Event | What updates |
|-------|----------------|
| User progresses a task / planner replans | `sessions/*/tasks.json` → `active_nodes` changes |
| Node YAML edited + graph DB rebuilt | `standards/**/*_graph.db` mtime changes |
| Optional `GRAPH_EXPLORER_AUTO_REBUILD=1` | YAML save triggers `build_pack_graph_db()` for affected pack |

The file watcher debounces changes (~350 ms) and pushes WebSocket messages. The UI applies **incremental deltas** when possible (preserving node positions; no full dagre relayout on every delta).

---

## 4. Module layout

```
dev/graph_explorer/
  __main__.py          # python -m dev.graph_explorer
  adapter.py           # TaskContextReader, GraphExplorerAdapter
  serializer.py        # JSON DTOs
  analysis.py          # Orphans, cycles, duplicates, components, hubs
  delta.py             # Snapshot diffing for WebSocket
  watcher.py           # watchdog on tasks.json + graph.db + YAML
  server.py            # Starlette REST + WebSocket
  requirements.txt     # starlette, uvicorn, watchdog (dev-only)
  package.json         # concurrently runs server + Vite
  web/                 # React application
    src/
      components/      # GraphCanvas, SidePanel, SearchBar, FilterBar, AnalysisPanel
      hooks/           # useGraphWebSocket
      store/           # Zustand graph store
      utils/           # dagre layout, node/edge colors
```

Tests: [`tests/dev/`](../tests/dev/)

---

## 5. Starting the explorer

### Prerequisites

- Python 3.12+ with project `requirements.txt` installed
- Node.js 18+
- Compiled graph databases: `python scripts/build_all_standards_dbs.py`
- Dev-only Python packages: `pip install -r dev/graph_explorer/requirements.txt`

### Terminal 1 — Desktop app

```bash
cd desktopApp
npm run dev
```

Create or activate an engineering task (e.g. Pipe Wall Thickness or MAWP) so `active_nodes` is non-empty.

### Terminal 2 — Graph explorer

```bash
cd dev/graph_explorer
npm run install:all
npm run dev
```

Open **http://localhost:3000**.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_ROOT` | repo root | Standards and sessions paths |
| `GRAPH_EXPLORER_HOST` | `127.0.0.1` | Dev server bind address |
| `GRAPH_EXPLORER_PORT` | `8765` | Dev server port |
| `GRAPH_EXPLORER_SESSION` | `auto` | Session / project id (`auto` picks the desktop project with an active task) |
| `DESKTOP_USER_DATA` | auto-detected on Windows dev | Must match Electron user data (see below) |
| `GRAPH_EXPLORER_AUTO_REBUILD` | `0` | `1` = rebuild graph DB on YAML change |

Use the same `PROJECT_ROOT` and `DESKTOP_USER_DATA` as Electron when testing packaged user data paths.

---

## 6. REST API (dev server only)

Base URL: `http://127.0.0.1:8765`  
No authentication (localhost only).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/api/graph/context` | Active task id, workflow, node/edge counts |
| GET | `/api/graph/snapshot` | Full subgraph; `?revision=` returns `{unchanged: true}` if unchanged |
| GET | `/api/graph/nodes/{id}` | Node detail for side panel |
| GET | `/api/graph/analysis` | Analysis report for current subgraph |
| GET | `/api/graph/search?q=` | Search by node id or name |
| WS | `/ws/graph` | Snapshot on connect; delta messages on change |

### WebSocket message types

**Snapshot** (initial connect or full refresh):

```json
{
  "type": "snapshot",
  "revision": "abc123…",
  "context": { "task_id": "…", "node_count": 42, "edge_count": 80 },
  "nodes": […],
  "edges": […]
}
```

**Delta** (incremental update):

```json
{
  "type": "delta",
  "revision": "def456…",
  "added_nodes": [],
  "removed_nodes": [],
  "changed_nodes": [],
  "added_edges": [],
  "removed_edges": []
}
```

If WebSocket disconnects, the UI polls `GET /api/graph/snapshot?revision=` every 3 seconds.

---

## 7. Browser UI features

| Feature | Description |
|---------|-------------|
| Canvas | React Flow: zoom, pan, minimap, fit-to-screen, draggable nodes (positions client-only) |
| Theme | Dark mode |
| Node colors | By `node_type` (workflow, equation, parameter, standard_section, assumption, etc.) |
| Edge colors | By `edge_type` (requires, calculates, validates, uses, …) |
| Search | Instant match on id/name; highlights and centers viewport |
| Filters | Toggle visibility per node type |
| Side panel | ID, name, type, description, inputs, outputs, edges, metadata, standard refs |
| Analysis | Orphans, no incoming/outgoing, cycles, duplicate names, disconnected components, highly connected nodes |

### Node type mapping

| UI label | Source `node_type` |
|----------|-------------------|
| Equation | `equation` |
| Parameter | `parameter` |
| Workflow | `workflow` |
| Standard | `standard_section` |
| Validator | `assumption`, `interaction` |
| Calculator | `calculation` (legacy) |
| Unit | Shown as metadata on parameters (`unit` field), not a separate node |

Materials are referenced in parameter/lookup metadata, not as standalone graph nodes today.

---

## 8. Graph analysis

Analysis runs on the **current visible subgraph** (active task), not the full pack.

| Metric | Definition |
|--------|------------|
| Orphan nodes | In-degree 0 and out-degree 0 |
| No incoming | In-degree 0 (excluding orphans) |
| No outgoing | Out-degree 0 (excluding orphans) |
| Cycles | Directed cycles via DFS |
| Duplicate names | Same normalized `title` / `symbol` on multiple nodes |
| Disconnected components | Connected components on undirected view |
| Highly connected | Total degree ≥ 5 (configurable in `analysis.py`) |

Results are clickable in the UI to focus the corresponding node.

---

## 9. Extension points

`GraphViewProvider` protocol in [`adapter.py`](../dev/graph_explorer/adapter.py):

```python
class GraphViewProvider(Protocol):
    def get_context(self) -> GraphContextDto: ...
    def get_snapshot(self) -> GraphSnapshotDto: ...
    def get_node(self, node_id: str) -> NodeDetailDto | None: ...
    def reload(self) -> None: ...
```

Planned future providers:

- `FullPackGraphProvider` — entire compiled pack (5k–10k nodes)
- `DependencyTraceProvider` — upstream/downstream from selected node
- `ImpactAnalysisProvider` — nodes affected by a change
- AI activity timeline, version history, performance metrics

Reserved WebSocket types: `snapshot`, `delta`, `analysis`, `activity`.

---

## 10. Testing

```bash
python -m pytest tests/dev
```

Frontend production build:

```bash
cd dev/graph_explorer/web
npm run build
```

---

## 11. Related documentation

- [Graph platform architecture](architecture/graph_platform.md) — compile-time graph pipeline
- [Graph engine design](core/14.%20graph_engine_design.md) — traversal and execution plans
- [Node Dev Studio](node_dev_studio.md) — YAML editing UI (complementary dev tool)
- [Backend UI contract](desktopApp/05_backend_ui_contract.md) — production desktop ↔ backend boundary
