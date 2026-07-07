# Node Dev Studio

Development-only web application for **authoring micro-graph nodes** in the Ver03 standards corpus. Edit YAML sources, validate relationships and equations, and sync the compiled graph database used by the desktop app at runtime.

The studio runs on localhost. In the desktop app, enable **Dev Mode** (header toggle) to use the inline **Node Edit** tab or open the full **Node Dev Studio** window. Packaged Electron builds include dev studio APIs when `VITE_ENABLE_DEV_TOOLS=true` (set in `npm run package:win`).

---

## 1. Purpose

Node Dev Studio helps developers and AI-assisted workflows maintain the engineering knowledge graph:

- Browse, search, and filter all nodes in a standards pack
- Create, edit, duplicate, and delete nodes with inline validation
- Edit relationships (`requires`, `calculates`, `contains`, etc.) via searchable multi-select
- Preview SymPy equations with Monaco editor and KaTeX rendering
- Bulk tag, delete, import, and export nodes (JSON, Markdown, CSV)
- Auto-refresh when the graph database changes (e.g. desktop app or another editor session)

**Source of truth:** `standards/{pack}/nodes/**/node.yaml` (and companion `node.md` for section paragraph trace)  
**Runtime cache:** `{pack}_graph.db` (incrementally updated on each save)

---

## 2. Isolation from production

| Property | Behavior |
|----------|----------|
| Frontend | Separate Vite entry: `desktopApp/studio.html` → `src/dev-studio/` |
| Backend | Gated routes under `/api/v1/dev/*`; returns 404 unless `DEV_STUDIO_ENABLED=1` |
| Desktop app | **Dev Mode** toggle (`devToolsStore.devModeActive`) gates inline Node Edit + optional `studio.html` window; lazy chunks load when `env.devToolsAvailable` |
| Release build | `studio.html` included when `VITE_ENABLE_DEV_TOOLS=true`; APIs enabled on all Electron backend spawns |
| SQLite access | Browser talks to Python API only — no direct DB access from the client |
| Disable | Unset `DEV_STUDIO_ENABLED` — production API behavior unchanged |

---

## 3. Architecture

```
Browser (studio.html :5173)
       │
       │  HTTP  /api/v1/dev/*
       ▼
api.server (:8000)  ── DevStudioService
       │
       ├── NodeRepository  →  standards/*/nodes/**/node.yaml  (write)
       └── graph_sync      →  *_graph.db                     (incremental upsert)
       │
       └── invalidate_standards_cache()  →  StandardsReader.reload()
                    │
                    ▼
Desktop app / task engine reads same graph DB without restart
```

### Write pipeline

1. Validate payload (required fields, unique IDs, SymPy syntax, broken refs, cycles)
2. Serialize metadata + markdown body → `node.yaml` via `compose_frontmatter()` (section nodes may also have a companion `node.md` for paragraph content and embedded `source:` blocks)
3. Incremental graph sync: `upsert_node` + rebuild edges for that node only
4. Bump pack revision hash; invalidate cached `StandardsReader`

Full pack rebuild (`python scripts/build_graph_db.py`) is still supported and remains the canonical batch compile path.

---

## 4. Quick start

### Prerequisites

- Python environment with project dependencies (`pip install -r requirements.txt`)
- Node.js for `desktopApp/`
- Standards pack with `nodes/` directory (e.g. `standards/asme/asme_b31.3/`)

### Terminal 1 — backend

From the **repository root** (`Ver03/`):

```powershell
cd C:\sideProject\AIEngineering\Ver03
$env:DEV_STUDIO_ENABLED="1"
python -m api.server
```

Or set `DEV_STUDIO_ENABLED=1` in repo-root `.env` (see `.env.example`).

### Terminal 2 — studio UI

From `desktopApp/` (not your home directory):

```powershell
cd C:\sideProject\AIEngineering\Ver03\desktopApp
npm install
npm run dev:studio
```

Open **http://127.0.0.1:5173/studio.html**

The desktop app (`npm run dev`) can run at the same time on the same backend.

### Environment variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `DEV_STUDIO_ENABLED=1` | Backend (repo root) | Enables `/api/v1/dev/*` routes |
| `VITE_BACKEND_URL` | `desktopApp/.env` | API base URL (default `http://localhost:8000`) |
| `VITE_DEV_STUDIO=true` | Vite only | Used by `dev:studio` script; skips Electron plugin |

---

## 5. User interface

Three-panel layout (dark theme, collapsible sections):

| Panel | Contents |
|-------|----------|
| **Left** | Search bar, node-type filter, virtual-scrolled node list, selection checkboxes, node count |
| **Center** | Property editor by type schema (General, Calculation, Engineering, Relationships, Body), equation editor, validation banner, save toolbar |
| **Right** | Mini dependency graph (SVG), incoming/outgoing edges, connected equations/workflows/sections (clickable) |

### Supported node types

Canonical micro-graph types: `workflow`, `equation`, `parameter`, `text`, plus kinds such as `assumption`, `interaction`, `table`, `lookup`, and section nodes. Field schemas are loaded from `GET /api/v1/dev/node-types` (see `api/dev_studio/serializers.py` and `docs/node-templates/`).

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+S` | Save current node |
| `Ctrl+F` | Focus search |
| `Ctrl+N` | Create new parameter node |
| `Ctrl+D` | Duplicate selected node |
| `Delete` | Delete selected node (with confirm) |
| `↑` / `↓` | Navigate node list |

### Auto-refresh

The UI polls `GET /api/v1/dev/revision?pack=` every 3 seconds (pauses when the tab is hidden). When the revision changes, the node list reloads and the selected node refreshes if there are no unsaved edits.

---

## 6. Features

### Search and filter

Server-side search across id, title, description, sympy, tags, unit, and category/topic. Client debounces input (250 ms). Type filter narrows by `node_type`.

### Validation (before save)

- Required fields per type
- Unique node IDs
- SymPy syntax for equation nodes
- Broken reference targets
- Circular dependency detection
- Duplicate title warnings

Errors and warnings appear inline in the center panel.

### Equation editor

For `equation` nodes: Monaco editor for `sympy`, KaTeX preview for `display_latex`, test-value evaluation via `POST .../equation/preview`.

### Bulk operations

Multi-select nodes in the left panel, then:

- Delete, add tags, export (JSON / CSV / Markdown)
- Import from `.json`, `.md`, or `.csv` (toolbar also offers import when nothing is selected)

### Import / export formats

| Format | Export | Import |
|--------|--------|--------|
| JSON | Array of `{ metadata, body, source_rel_path }` | Full node payloads |
| Markdown | `node.yaml` content per file | YAML frontmatter + body |
| CSV | id, type, title, path, description | Parameter stubs or `metadata` JSON column |

---

## 7. REST API

All routes require `DEV_STUDIO_ENABLED=1`. Most endpoints accept `?pack=asme_b31.3` (default pack).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dev/packs` | List packs with node counts and revision |
| GET | `/api/v1/dev/node-types` | Type schemas and field groupings |
| GET | `/api/v1/dev/nodes` | List node summaries (`?type=` optional) |
| GET | `/api/v1/dev/search` | Search (`?q=&type=`) |
| GET | `/api/v1/dev/nodes/{id}` | Full node detail |
| POST | `/api/v1/dev/nodes` | Create node |
| PUT | `/api/v1/dev/nodes/{id}` | Update node |
| DELETE | `/api/v1/dev/nodes/{id}` | Delete node |
| POST | `/api/v1/dev/nodes/{id}/duplicate` | Clone with new id |
| POST | `/api/v1/dev/nodes/validate` | Dry-run validation |
| POST | `/api/v1/dev/nodes/{id}/equation/preview` | SymPy evaluate test values |
| GET | `/api/v1/dev/relationships` | `?node_id=` incoming/outgoing graph |
| GET | `/api/v1/dev/revision` | Pack revision hash for polling |
| POST | `/api/v1/dev/nodes/bulk` | Bulk delete / tags / topic |
| GET | `/api/v1/dev/export` | `?format=json\|markdown\|csv&ids=` |
| POST | `/api/v1/dev/import` | Batch import |

---

## 8. Code layout

### Backend

```
api/dev_studio/
  service.py           # CRUD, search, bulk, import/export
  node_repository.py   # YAML read/write under standards/*/nodes/
  graph_sync.py        # Incremental *_graph.db sync
  validation.py        # Pre-save validation
  serializers.py       # API DTOs and type schemas
  revision.py          # Pack revision hashing
  routes.py            # HTTP handlers + env gate
```

Wired in `api/server.py` when `DEV_STUDIO_ENABLED` is set.

### Frontend

```
desktopApp/
  studio.html
  src/dev-studio/
    main.tsx
    DevStudioApp.tsx
    api/devStudioApi.ts
    store/devStudioStore.ts
    components/
      sidebar/NodeListPanel.tsx
      editor/NodeEditorPanel.tsx
      graph/GraphPanel.tsx, MiniDependencyGraph.tsx
      relationships/RelationshipEditor.tsx
      equation/EquationEditor.tsx
      fields/FieldComponents.tsx
      bulk/BulkActionBar.tsx
    hooks/useDebouncedSearch.ts, useRevisionPoll.ts
    styles/dev-studio.css
```

Reusable field and relationship components are intended for future editors (materials, standards, workflows).

---

## 9. Testing

```powershell
# Backend
python -m pytest tests/api/test_dev_studio_crud.py tests/api/test_dev_studio_validation.py tests/api/test_dev_studio_search.py tests/api/test_dev_studio_import.py

# Frontend
cd desktopApp
npm run test:run -- tests/dev-studio
```

---

## 10. Related tools

| Tool | Role |
|------|------|
| **Node Dev Studio** (this doc) | **Read/write** authoring of YAML node sources |
| `scripts/build_graph_db.py` | Full pack recompile (batch) |
| `docs/node-templates/` | YAML templates for each node type |

After large manual edits outside the studio, run `python scripts/build_all_standards_dbs.py` and backend tests to verify consistency.

---

## 11. Troubleshooting

**`ENOENT: no such file or directory, package.json`**  
Run npm from `desktopApp/`, not your home directory or the repo root.

**Dev API returns 404**  
Set `DEV_STUDIO_ENABLED=1` before starting `python -m api.server`.

**Changes not visible in desktop app**  
Confirm the backend process received the save (check studio validation errors). The studio invalidates `StandardsReader` cache on write; restart the backend only if you edited files on disk outside the API.

**Node not found after duplicate**  
Duplicate writes to a new folder derived from node type and id. Ensure the new id is unique and validation passes.
