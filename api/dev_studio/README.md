# `api/dev_studio/` — Architecture Audit

Audit date: 2026-07-01. Development-only **Node Dev Studio** backend: CRUD on `standards/*/nodes/**/node.yaml`, incremental `*_graph.db` sync, validation. Parent overview: [../README.md](../README.md).

---

## Purpose

Expose gated REST endpoints (`/api/v1/dev/*`) for editing micro-graph node sources on disk. The studio UI (`desktopApp` Vite `dev:studio` entry) calls these routes; production desktop builds do not include the studio unless explicitly configured.

**Gate:** `DEV_STUDIO_ENABLED=1` (or `true` / `yes`). When unset, all dev routes return **404** via `require_dev_studio`.

---

## Entry Points

| Entry | Role |
|-------|------|
| `api/dev_studio/routes.py` | HTTP handlers called from `server.ApiHandler` |
| `DevStudioService` | Business logic; constructed in `server._build_dev_studio()` |
| `api/dev_studio/__init__.py` | Re-exports `DevStudioService` |

---

## Runtime Usage

```text
server.main()
  → _build_dev_studio(service)  [if DEV_STUDIO_ENABLED]
  → DevStudioService(standards_root, on_pack_changed=invalidate_standards_cache)
  → ApiHandler.dev_studio

HTTP /api/v1/dev/*
  → handle_dev_get | post | put | delete (routes.py)
  → DevStudioService
  → NodeRepository (YAML files)
  → graph_sync (SQLite *_graph.db)
```

Electron dev (`backendProcess.ts`) sets `DEV_STUDIO_ENABLED=1` when `enableDevStudio` is true.

---

## Dependencies (outbound)

| Module | Use |
|--------|-----|
| `api.desktop_service.ApiError` | HTTP errors |
| `engine.reference.*` | Graph DB, compile edges, node types, markdown YAML |
| `engine.graph.graph_builder` | Source fingerprint (revision) |
| `engine.equation.sympy_evaluator` | Equation preview |

## Dependents (inbound)

| Consumer | Usage |
|----------|-------|
| `api/server.py` | Routes + service construction |
| `desktopApp/src/dev-studio/api/devStudioApi.ts` | HTTP client |
| `tests/api/test_dev_studio_*.py` | Direct `DevStudioService` / route tests |

---

## REST Routes (`routes.py`)

Default pack query: `?pack=asme_b31.3`. Pack may also be passed in JSON body as `"pack"`.

### GET

| Path | `DevStudioService` method |
|------|---------------------------|
| `/api/v1/dev/packs` | `list_packs()` |
| `/api/v1/dev/node-types` | `get_node_types()` |
| `/api/v1/dev/nodes?type=` | `list_nodes(pack, node_type)` |
| `/api/v1/dev/nodes/{id}` | `get_node(pack, id)` |
| `/api/v1/dev/search?q=&type=` | `search_nodes()` |
| `/api/v1/dev/revision` | `get_revision(pack)` |
| `/api/v1/dev/relationships?node_id=` | `get_relationships(pack, node_id)` |
| `/api/v1/dev/export?format=json\|markdown\|csv&ids=` | `export_nodes()` |

### POST

| Path | Status | Method |
|------|--------|--------|
| `/api/v1/dev/nodes` | 201 | `create_node(pack, body)` |
| `/api/v1/dev/nodes/validate` | 200 | `validate_payload(...)` |
| `/api/v1/dev/nodes/bulk` | 200 | `bulk_action(pack, body)` — delete, add_tags, remove_tags, set_topic |
| `/api/v1/dev/import` | 200 | `import_nodes(pack, body)` — json, markdown, csv |
| `/api/v1/dev/nodes/{id}/duplicate` | 201 | `duplicate_node(pack, id, new_id, …)` |
| `/api/v1/dev/nodes/{id}/equation/preview` | 200 | `preview_equation(pack, id, body)` |

### PUT

| Path | Method |
|------|--------|
| `/api/v1/dev/nodes/{id}` | `update_node(pack, id, body)` — supports rename via metadata.id + `force` |

### DELETE

| Path | Method |
|------|--------|
| `/api/v1/dev/nodes/{id}` | `delete_node(pack, id)` |

---

## Execution Trace: create node

```text
POST /api/v1/dev/nodes
  → handle_dev_post → DevStudioService.create_node
  → validate_payload (validation.py)
  → NodeRepository.write_node → standards/.../nodes/.../node.yaml
  → sync_node_to_graph_db (graph_sync.py)
  → on_pack_changed → DesktopApiService.invalidate_standards_cache
  → get_node → JSON node detail
```

---

## Files

| File | Role |
|------|------|
| `routes.py` | Env gate, path dispatch, pack query parsing |
| `service.py` | CRUD, search, import/export, bulk, equation preview |
| `node_repository.py` | Discover/read/write/delete YAML node files |
| `graph_sync.py` | Incremental upsert/delete in pack `*_graph.db` |
| `validation.py` | Schema, references, cycles, SymPy syntax |
| `serializers.py` | `NODE_TYPE_SCHEMAS`, API DTOs for list/detail/types |
| `revision.py` | Pack revision hash for UI auto-refresh |
| `__init__.py` | Export `DevStudioService` |

---

## Per-file inventory

### `routes.py`

- **Public:** `dev_studio_enabled`, `require_dev_studio`, `handle_dev_get`, `handle_dev_post`, `handle_dev_put`, `handle_dev_delete`
- **Imports:** `ApiError`, `DevStudioService`
- **Imported by:** `server.py`, tests
- **Active:** When `DEV_STUDIO_ENABLED` — **High**

### `service.py`

- **Public:** `DevStudioService` (full CRUD + import/export/bulk/preview)
- **Side effects:** Writes YAML directories; mutates SQLite graph DB; calls `on_pack_changed`
- **Imports:** `node_repository`, `graph_sync`, `revision`, `serializers`, `validation`, engine modules
- **Imported by:** `routes`, `server`, `__init__`, tests
- **Active:** Yes (gated) — **High**

### `node_repository.py`

- **Public:** `NodeRepository`, `StoredNode`
- **Side effects:** Filesystem CRUD under `standards/<pack>/nodes/`
- **Imports:** `engine.reference.standards_markdown`, `graph_compile`, `standards_paths`
- **Imported by:** `service.py`
- **Active:** Yes — **High**

### `graph_sync.py`

- **Public:** `sync_node_to_graph_db`, `remove_node_from_graph_db`
- **Side effects:** SQLite graph DB schema, nodes, edges, fingerprint meta
- **Imported by:** `service.py`
- **Active:** Yes — **High**

### `validation.py`

- **Public:** `validate_node_payload`, `ValidationResult`
- **Imports:** `NODE_TYPE_SCHEMAS`, SymPy parser
- **Imported by:** `service.py`, tests
- **Active:** Yes — **High**

### `serializers.py`

- **Public:** `NODE_TYPE_SCHEMAS`, `node_summary`, `node_detail`, `list_node_types`, `relationships_payload`
- **Imported by:** `service.py`, `validation.py`
- **Active:** Yes — **High**

### `revision.py`

- **Public:** `PackRevision`, `compute_pack_revision`
- **Imports:** `compute_source_fingerprint`, `build_or_load_graph`
- **Imported by:** `service.py`
- **Active:** Yes — **High**

### `__init__.py`

- **Public:** `DevStudioService` in `__all__`
- **Active:** Yes — **High**

---

## Possible Dead Code

| Symbol | Notes | Confidence |
|--------|-------|------------|
| `node_repository._DEFAULT_TYPE_PATHS`, `_KIND_PATHS` | Not used by `_default_rel_path` (always `nodes/{node_id}`) | **Medium** |
| `service._revision_cache` | Populated on change but `get_revision` always recomputes via `compute_pack_revision` | **Medium** — cache only invalidated, never read |

---

## Notes

- **Rename safety:** `update_node` blocks ID renames when other nodes reference the old ID unless `force: true`.
- **Reference detection:** `_find_references` uses substring search in `json.dumps(metadata)` — coarse, not graph-aware.
- **List/search fallback:** When graph DB row missing, summaries are built from YAML metadata only.
- **Import formats:** JSON array, markdown files (multi-doc split), CSV with optional JSON `metadata` column.
- **Tests:** `tests/api/test_dev_studio_crud.py`, `test_dev_studio_validation.py`, `test_dev_studio_search.py`, `test_dev_studio_import.py`.

---

## Desktop client mapping

All routes mirrored in `desktopApp/src/dev-studio/api/devStudioApi.ts`.
