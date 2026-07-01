# scripts/ — Architecture Audit

Audit date: 2026-07-01. Documentation reflects the code as it exists today; no architectural recommendations.

---

## Purpose

**Offline build and migration utilities** for the standards micro-graph platform. Scripts compile Markdown/YAML sources under `knowledge/standards/` into SQLite caches (`*_graph.db`, `*_nodes.db`, `*_tables.db`, `workflows.db`, `standards_config.db`, material catalog, pipe dimensions). They are invoked manually, from docs/CI instructions, from tests, and in one case from the Graph Explorer file watcher.

Scripts are **not** imported by the desktop REST API during normal user workflows except where noted (Graph Explorer watcher).

---

## Files

### Python scripts (root)

| File | Role |
|------|------|
| `build_all_standards_dbs.py` | Orchestrator: runs most build scripts in sequence for a full standards rebuild. |
| `build_graph_db.py` | Compiles pack sources → `PackGraph` → `*_graph.db` per standard pack. |
| `build_standards_nodes_db.py` | Discovers node YAML/MD → `{pack}_nodes.db`; may delete legacy flat duplicates. |
| `build_standards_tasks_db.py` | Compiles `{pack}/nodes/workflows/*.yaml` → global `workflows.db`. |
| `build_standards_registry_db.py` | Compiles registry YAML → `standards_config.db`. |
| `build_standards_tables_db.py` | Seeds ASME B31.3 lookup tables into `{pack}_tables.db` (hardcoded sample data). |
| `build_astm_standards_tables_db.py` | Builds ASTM pack `*_tables.db` from seed YAML files. |
| `build_material_catalog_db.py` | Rebuilds global material search catalog from registry + ASTM tables. |
| `build_pipe_dimensions_db.py` | Imports pipe dimension YAML → per-pack `pipe_dimensions.db`. |
| `flatten_b313_nodes.py` | One-time migration: flatten B31.3 `nodes/` tree to `nodes/{node_id}/`. |
| `inline_b313_node_assets.py` | Migration: inline per-node asset subfolders into parent `node.yaml`. |
| `merge_b313_node_sources.py` | Migration: merge dual `node.yaml` + `node.md` into single `node.yaml`. |
| `migrate_b313_graph_nodes.py` | Historical migration: `graph/nodes` → hierarchical `nodes/` (superseded). |
| `generate_pipe_wall_graph_nodes.py` | Generator: writes B31.3 pipe-wall workflow node YAML under `standards/`. |

### `seeds/` (YAML data)

| File | Role |
|------|------|
| `astm_a53_material_properties.yaml` | Seed table for ASTM A53 material properties. |
| `astm_a106_material_properties.yaml` | Seed table for ASTM A106 grades. |
| `astm_a312_material_properties.yaml` | Seed table for ASTM A312 stainless pipe. |
| `astm_a105_material_properties.yaml` | Seed table for ASTM A105 forgings. |

---

## Entry Points

All `*.py` files in this folder are runnable via `python scripts/<name>.py` (`if __name__ == "__main__"` present on each). Typical invocations are documented in `README.md`, `AGENTS.md`, and standards docs.

| Script | Primary `__main__` action |
|--------|---------------------------|
| `build_all_standards_dbs.py` | `build_all()` |
| `build_graph_db.py` | `build_all()` |
| `build_standards_nodes_db.py` | `build_all()` |
| `build_standards_tasks_db.py` | `build_all()` |
| `build_standards_registry_db.py` | `build_all()` |
| `build_standards_tables_db.py` | `build_database()` |
| `build_astm_standards_tables_db.py` | `build_all()` |
| `build_material_catalog_db.py` | `build_all()` |
| `build_pipe_dimensions_db.py` | `build_all()` |
| `flatten_b313_nodes.py` | `flatten()` via `main()` |
| `inline_b313_node_assets.py` | `run()` via `main()` |
| `merge_b313_node_sources.py` | `run()` via `main()` |
| `migrate_b313_graph_nodes.py` | `migrate()` |
| `generate_pipe_wall_graph_nodes.py` | `main()` |

**Programmatic entry points** (imported by other code):

| Callable | Imported by |
|----------|-------------|
| `build_graph_db.build_pack_graph_db` | `dev/graph_explorer/watcher.py` |
| `build_graph_db.build_all` | `build_all_standards_dbs.py` |
| `build_astm_standards_tables_db.build_all` | `build_all_standards_dbs.py`, `build_material_catalog_db.py` |
| `build_astm_standards_tables_db.import_material_properties_pack` | Internal to `build_astm_standards_tables_db.py` only |
| `build_material_catalog_db.build_all` | `build_all_standards_dbs.py` |
| `build_pipe_dimensions_db.build_all` | `build_all_standards_dbs.py`, `tests/reference/test_pipe_dimensions_db.py` |
| `build_standards_nodes_db.build_pack`, `build_all` | `build_all_standards_dbs.py`, `tests/reference/test_build_standards_nodes_db.py` |
| `build_standards_registry_db.build_all` | `build_all_standards_dbs.py`, `tests/reference/test_standards_config_db.py` |
| `build_standards_tasks_db.build_all` | `tests/reference/test_standards_tasks_db.py` only |
| `build_standards_tables_db.build_database` | `build_all_standards_dbs.py` |

Seed YAML files are read only by `build_astm_standards_tables_db.py` (paths hardcoded in `build_all()` pack list).

---

## Dependencies

### This folder depends on

| Area | Examples |
|------|----------|
| `engine/reference/*` | `standards_nodes`, `standards_tables`, `graph_cache`, `pack_graph_db`, `material_catalog_db`, `pipe_dimensions_db`, `standards_config_db`, `standards_markdown`, `embedded_nodes`, `standards_paths` |
| `engine/graph/graph_builder.py` | `build_graph_db.py` |
| `standards/` tree | Source markdown/YAML, registry YAML, task roots |
| Other scripts | `build_all_standards_dbs.py` chains most builders; `build_material_catalog_db.py` calls `build_astm_standards_tables_db` |
| Third-party | `yaml` (PyYAML) where used |

### Who depends on this folder

| Consumer | Relationship |
|----------|--------------|
| `build_all_standards_dbs.py` | Imports other scripts |
| `dev/graph_explorer/watcher.py` | Imports `build_pack_graph_db` on file change |
| `tests/reference/*`, `tests/mvp/test_node_and_standard_content.py` | Import builders or assume DBs exist |
| `engine/graph/graph_engine.py`, `engine/reference/standards_reader.py`, `engine/reference/material_catalog_db.py`, `engine/executor/*_resolver.py` | Error messages reference script names; runtime reads built SQLite |
| `README.md`, `AGENTS.md`, `docs/*` | Document manual invocation |
| `api/desktop_service.py` | Does **not** import scripts; expects pre-built DBs |

---

## Runtime Usage

**Partially on the execution path.**

| Context | On path? | Evidence |
|---------|----------|----------|
| Normal desktop/API session | **No** (reads pre-built SQLite) | `StandardsReader`, `GraphEngine` load `*_graph.db` / `*_nodes.db`; missing DB errors cite scripts |
| Developer rebuild | **Yes** (manual) | `python scripts/build_all_standards_dbs.py` per `AGENTS.md` |
| Graph Explorer dev mode | **Yes** (optional) | `watcher.py` calls `build_pack_graph_db` on `.yaml`/`.md` changes |
| CI / tests | **Yes** | Tests import `build_*` functions or skip if DBs missing |
| B31.3 migration scripts | **No** (historical / one-off) | Only referenced in docs; not imported by runtime |

Post-build runtime flow (after scripts have been run):

```
standards/*/nodes/**/node.yaml
    ↓ (already compiled)
{pack}_graph.db / {pack}_nodes.db
    ↓
engine/reference/standards_reader.py + engine/graph/graph_engine.py
    ↓
api/desktop_service.py → task_state / workflow execution
    ↓
desktopApp UI
```

---

## Possible Dead Code

| Item | Why it appears unused | Confidence |
|------|----------------------|------------|
| `migrate_b313_graph_nodes.py` | Docstring marks historical; expects `standards/.../graph/nodes` which migration removed | **High** |
| `inline_b313_node_assets.py` | No Python importers; docs describe completed migration | **High** |
| `merge_b313_node_sources.py` | No Python importers; docs say merge completed 2026-06-30 | **High** |
| `flatten_b313_nodes.py` | No Python importers; one-time layout migration | **High** |
| `generate_pipe_wall_graph_nodes.py` | No importers; overwrites/generates nodes if re-run | **Medium** |
| `build_standards_tasks_db.build_all` import in `build_all_standards_dbs.py` | Imported as `build_tasks` but **never called** in `build_all()` | **High** |
| `build_standards_nodes_db._collect_assets` | Always returns `[]`; superseded by `_collect_embedded_assets` | **High** |
| `build_standards_registry_db` imports `load_material_registry`, `load_supplemental_materials`, `load_pipe_dimensions_registry` | Unused; script uses local `_load_*_yaml` instead | **High** |

Do not delete based on this audit alone.

---

## Notes

- **`build_all_standards_dbs.py` omits `build_tasks()`** — `workflows.db` is not rebuilt by the orchestrator despite the import. Developers must run `build_standards_tasks_db.py` separately (or tests call it directly).
- **Two parallel compile paths for graphs**: `build_graph_db.py` (`GraphBuilder` → `*_graph.db`) vs `build_standards_nodes_db.py` (`StandardsNodesDatabase` → `*_nodes.db`). Both scan similar sources; purposes differ (execution graph vs browse/index DB).
- **B31.3 tables script uses embedded data** — `build_standards_tables_db.py` hardcodes sample rows; not loaded from `standards/` markdown.
- **ASTM tables use `scripts/seeds/`** — consolidated pack at `knowledge/standards/astm/`; build writes per-material `*_tables.db` at pack root from `scripts/seeds/*.yaml`.
- **`build_standards_nodes_db._remove_flat_duplicates`** deletes legacy folder trees under B31.3 during build (side effect on source tree, not only SQLite).
- **No `scripts/__init__.py`** — imports use `from scripts.X import ...` with repo root on `sys.path`.

---

## Per-file documentation

### `build_all_standards_dbs.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Single command to rebuild most standards SQLite artifacts. |
| **Public functions** | `build_all(*, standards_root=None, rebuild_astm=True)` |
| **Inputs** | `standards/` tree; optional `standards_root`. |
| **Outputs** | Prints progress; writes multiple `*.db` files via delegated builders. |
| **Side effects** | Invokes builders that may delete/recreate DB files and (via nodes builder) legacy source folders. |
| **Imported by** | None (top-level orchestrator). |
| **Imports** | `scripts.build_astm_standards_tables_db`, `build_material_catalog_db`, `build_pipe_dimensions_db`, `build_standards_nodes_db`, `build_standards_registry_db`, `build_standards_tables_db`, `build_standards_tasks_db` (unused call), lazy `build_graph_db`. |
| **Actively used** | Yes — documented primary rebuild entry. |
| **Confidence** | **High** |

---

### `build_graph_db.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Compile pack node sources into micro-graph SQLite cache (`*_graph.db`). |
| **Public functions** | `build_pack_graph_db(pack_root)`, `build_all(*, standards_root=None)` |
| **Inputs** | Pack `nodes/` directory under each standard pack. |
| **Outputs** | Path to written graph DB per pack. |
| **Side effects** | Writes/overwrites SQLite via `write_graph_cache`. |
| **Imported by** | `build_all_standards_dbs.py`, `dev/graph_explorer/watcher.py`. |
| **Imports** | `engine.graph.graph_builder.GraphBuilder`, `engine.reference.graph_cache`, `pack_graph_db`, `standards_paths`. |
| **Actively used** | Yes. |
| **Confidence** | **High** |

---

### `build_standards_nodes_db.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Build per-pack node index DB (`*_nodes.db`) from `node.yaml`/`node.md`, embedded children, and `index.md`. |
| **Public functions** | `build_pack(pack_root)`, `build_all(*, standards_root=None)` |
| **Private helpers** | `_discover_nodes`, `_collect_embedded_assets`, `_collect_assets` (stub), `_parse_index_md`, `_remove_flat_duplicates`, etc. |
| **Inputs** | Pack `nodes/`, `index.md`. |
| **Outputs** | SQLite node DB; console summary. |
| **Side effects** | `clear_all` on DB; may `shutil.rmtree` legacy duplicate B31.3 node folders during build. |
| **Imported by** | `build_all_standards_dbs.py`, `tests/reference/test_build_standards_nodes_db.py`. |
| **Imports** | `engine.reference.pack_nodes_db`, `embedded_nodes`, `standards_markdown`, `standards_nodes`, `standards_paths`. |
| **Actively used** | Yes. |
| **Confidence** | **High** |

---

### `build_standards_tasks_db.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Compile workflow YAML from `{pack}/nodes/workflows/*.yaml` into `knowledge/standards/workflows.db`. |
| **Public functions** | `build_all(*, standards_root=None)` |
| **Inputs** | Workflow `*.yaml` files with `type: workflow` frontmatter. |
| **Outputs** | `Path` to `workflows.db` or `None` if no workflows. |
| **Side effects** | Clears and repopulates global tasks DB. |
| **Imported by** | `build_all_standards_dbs.py` (import only, not invoked), `tests/reference/test_standards_tasks_db.py`. |
| **Imports** | `engine.reference.standards_markdown`, `standards_paths`, `standards_tasks_db`. |
| **Actively used** | Yes, but not via orchestrator. |
| **Confidence** | **High** |

---

### `build_standards_registry_db.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Compile `knowledge/global/materials/registry.yaml`, supplemental materials, and pipe dimension registry into `standards_config.db`. |
| **Public functions** | `build_all(*, standards_root=None)` |
| **Private helpers** | `_load_material_registry_yaml`, `_load_supplemental_yaml`, `_load_pipe_registry_yaml` |
| **Inputs** | Registry YAML files under `standards/`. |
| **Outputs** | `standards_config.db` path. |
| **Side effects** | `clear_all` + upserts on config DB. |
| **Imported by** | `build_all_standards_dbs.py`, `tests/reference/test_standards_config_db.py`. |
| **Imports** | `yaml`, `engine.reference.material_catalog_db` (partially unused loaders), `pipe_dimensions_registry`, `standards_config_db`. |
| **Actively used** | Yes. |
| **Confidence** | **High** |

---

### `build_standards_tables_db.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Populate ASME B31.3 `{pack}_tables.db` with hardcoded lookup tables (A-1 sample, A-1A, A-1B, 304.1.1, 302.3.5, 302.3.3C). |
| **Public functions** | `build_database(db_path=_DB_PATH)` |
| **Inputs** | Inline Python constants (`_STRESS_MATERIALS`, `_TABLE_304_1_1_MATERIALS`, etc.). |
| **Outputs** | `StandardsTablesDatabase` instance. |
| **Side effects** | `clear_all_tables` + upserts; writes SQLite. |
| **Imported by** | `build_all_standards_dbs.py`. |
| **Imports** | `engine.reference.asme_b31_3_table_ids`, `material_ids`, `pack_tables_db`, `standards_tables`. |
| **Actively used** | Yes — required for B31.3 table lookups. |
| **Confidence** | **High** |

---

### `build_astm_standards_tables_db.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Build ASTM pack material-properties tables from YAML (seed or pack `tables/`). |
| **Public functions** | `import_material_properties_pack(...)`, `build_all()` |
| **Inputs** | Pack roots + `scripts/seeds/astm_*_material_properties.yaml`. |
| **Outputs** | List of `*_tables.db` paths. |
| **Side effects** | Deletes existing pack tables DB before rebuild. |
| **Imported by** | `build_all_standards_dbs.py`, `build_material_catalog_db.py`. |
| **Imports** | `yaml`, `engine.reference.material_ids`, `pack_tables_db`, `standards_tables`. |
| **Actively used** | Yes. |
| **Confidence** | **High** |

---

### `build_material_catalog_db.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Build global ASTM material search catalog SQLite from registry + source tables. |
| **Public functions** | `build_all(*, rebuild_astm=True)` |
| **Inputs** | `knowledge/global/materials/registry.yaml`; optionally rebuilds ASTM tables first. |
| **Outputs** | Material catalog DB path. |
| **Side effects** | `catalog.rebuild()`; may invoke ASTM table build. |
| **Imported by** | `build_all_standards_dbs.py`. |
| **Imports** | `engine.reference.material_catalog_db`, `scripts.build_astm_standards_tables_db`. |
| **Actively used** | Yes. |
| **Confidence** | **High** |

---

### `build_pipe_dimensions_db.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Import pipe dimension YAML sources into per-pack `pipe_dimensions.db`. |
| **Public functions** | `build_all(*, standards_root=None)`, `build_pack(standard, *, standards_root=None)` |
| **Inputs** | `standards/pipe_dimensions/registry.yaml` + pack YAML paths. |
| **Outputs** | List of DB paths (or single path for `build_pack`). |
| **Side effects** | Unlinks existing DB before import. |
| **Imported by** | `build_all_standards_dbs.py`, `tests/reference/test_pipe_dimensions_db.py`. |
| **Imports** | `engine.reference.pipe_dimensions_db`, `pipe_dimensions_registry`, `standards_paths`. |
| **Actively used** | Yes. |
| **Confidence** | **High** |

---

### `flatten_b313_nodes.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Flatten nested B31.3 `nodes/` directories to `nodes/{node_id}/` without editing node content. |
| **Public functions** | `flatten(*, dry_run=False)`, `main()` |
| **Inputs** | `standards/asme/asme_b31.3/nodes/`. |
| **Outputs** | Console summary; filesystem moves/deletes. |
| **Side effects** | Moves directories, removes embedded duplicates and empty dirs. |
| **Imported by** | None. |
| **Imports** | `engine.reference.embedded_nodes`, `standards_markdown`. |
| **Actively used** | No — migration tool only. |
| **Confidence** | **High** |

---

### `inline_b313_node_assets.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Inline `equations/`, `conditions/`, `notes/`, `references/` asset files into parent `node.yaml` `source:` blocks; convert `node.md` → `node.yaml`; fix cross-refs. |
| **Public functions** | `run(*, dry_run)`, `main()` |
| **Inputs** | B31.3 pack nodes with asset subfolders or stale `file:` refs. |
| **Outputs** | Console stats; rewritten YAML; deleted asset files/dirs. |
| **Side effects** | Extensive filesystem mutations under `standards/asme/asme_b31.3/nodes/`. |
| **Imported by** | None. |
| **Imports** | `engine.reference.standards_markdown`. |
| **Actively used** | No — migration tool only. |
| **Confidence** | **High** |

---

### `merge_b313_node_sources.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Merge folders that contain both `node.yaml` and `node.md` into a single `node.yaml`. |
| **Public functions** | `discover_dual_node_dirs`, `merge_dual_node_dir`, `run(*, dry_run)`, `main()` |
| **Inputs** | Top-level dirs under B31.3 `nodes/` with dual sources. |
| **Outputs** | Merged YAML; deletes `node.md`. |
| **Side effects** | Writes/deletes node source files. |
| **Imported by** | None. |
| **Imports** | `engine.reference.standards_markdown`. |
| **Actively used** | No — migration tool only. |
| **Confidence** | **High** |

---

### `migrate_b313_graph_nodes.py`

| Field | Detail |
|-------|--------|
| **Purpose** | One-time move from `standards/.../graph/nodes/` to `nodes/`; mark legacy files superseded; remove `graph/` tree. |
| **Public functions** | `migrate()` |
| **Inputs** | Legacy `PACK/graph/nodes/` layout. |
| **Outputs** | Console log; new `nodes/{id}/node.yaml` files. |
| **Side effects** | Removes entire `graph/` directory when done. |
| **Imported by** | None. |
| **Imports** | stdlib only (`re`, `shutil`, `pathlib`). |
| **Actively used** | No — historical. |
| **Confidence** | **High** |

---

### `generate_pipe_wall_graph_nodes.py`

| Field | Detail |
|-------|--------|
| **Purpose** | Generate initial B31.3 micro-graph node YAML for pipe wall thickness and MAWP workflows (workflows, sections, equations, parameters). |
| **Public functions** | `write_node`, `write_param`, `main()` |
| **Inputs** | Hardcoded `PARAMS`, section templates, `PATHS` dict. |
| **Outputs** | Writes `node.yaml` files under `standards/asme/asme_b31.3/nodes/`. |
| **Side effects** | Creates/overwrites node source files. |
| **Imported by** | None. |
| **Imports** | stdlib `pathlib` only. |
| **Actively used** | No at runtime — generator for initial content. |
| **Confidence** | **Medium** (could be re-run manually). |

---

### `seeds/astm_a53_material_properties.yaml`

| Field | Detail |
|-------|--------|
| **Purpose** | Development reference data for ASTM A53 carbon steel pipe mechanical properties and grade aliases. |
| **Public API** | YAML keys: `table_id`, `title`, `standard`, `keys`, `aliases`, `materials`, etc. |
| **Inputs** | Read by `build_astm_standards_tables_db.build_all()` pack entry for `astm_a53`. |
| **Outputs** | Becomes rows in `standards/astm/astm_a53/*_tables.db`. |
| **Side effects** | None (data file). |
| **Imported by** | `build_astm_standards_tables_db.py` (path literal). |
| **Imports** | None. |
| **Actively used** | Yes, when ASTM tables are built. |
| **Confidence** | **High** |

---

### `seeds/astm_a106_material_properties.yaml`

| Field | Detail |
|-------|--------|
| **Purpose** | Development reference data for ASTM A106 seamless carbon steel pipe (grades A/B/C). |
| **Imported by** | `build_astm_standards_tables_db.py` (`astm_a106` pack). |
| **Actively used** | Yes, when ASTM tables are built. |
| **Confidence** | **High** |

(Same structure as A53 seed; full key list omitted for brevity — file contains `materials` with grade entries and chemical/mechanical properties.)

---

### `seeds/astm_a312_material_properties.yaml`

| Field | Detail |
|-------|--------|
| **Purpose** | Development reference data for ASTM A312 austenitic stainless pipe (TP304, TP316, etc.). |
| **Imported by** | `build_astm_standards_tables_db.py` (`astm_a312` pack). |
| **Actively used** | Yes. |
| **Confidence** | **High** |

---

### `seeds/astm_a105_material_properties.yaml`

| Field | Detail |
|-------|--------|
| **Purpose** | Development reference data for ASTM A105 carbon steel forgings. |
| **Imported by** | `build_astm_standards_tables_db.py` (`a_105` pack). |
| **Actively used** | Yes. |
| **Confidence** | **High** |

---

## Execution traces

### Full standards rebuild (developer)

```
Developer: python scripts/build_all_standards_dbs.py
    ↓
build_standards_tables_db.build_database()        → asme_b31.3 *_tables.db
    ↓
build_astm_standards_tables_db.build_all()        → astm/*_tables.db at pack root (reads scripts/seeds/*.yaml)
    ↓
build_graph_db.build_all()                        → */*_graph.db
    ↓
build_standards_nodes_db.build_all()              → */*_nodes.db (may prune legacy folders)
    ↓
build_standards_registry_db.build_all()           → standards_config.db
    ↓
build_material_catalog_db.build_all()             → material catalog DB
    ↓
build_pipe_dimensions_db.build_all()              → pipe_dimensions.db per pack
    ↓
(NOT CALLED: build_standards_tasks_db.build_all)  → workflows.db unchanged by orchestrator
```

### Graph Explorer live rebuild

```
File change under standards/<org>/<pack>/nodes/**
    ↓
dev/graph_explorer/watcher.py → GraphChangeHandler._maybe_rebuild_pack()
    ↓
scripts/build_graph_db.build_pack_graph_db(pack_root)
    ↓
engine/graph/graph_builder.GraphBuilder.build() → write_graph_cache()
```

### Runtime task execution (uses script output, not scripts)

```
User starts task in desktop app
    ↓
api/desktop_service.py → workflow_bootstrap.bootstrap_new_task()
    ↓
engine/graph/graph_engine.py (loads *_graph.db)
    ↓
engine/reference/standards_reader.py (loads *_nodes.db, tables DBs)
    ↓
Planner / executor resolvers (e.g. allowable_stress_resolver — errors cite build_standards_tables_db.py)
```

### Historical B31.3 layout migration chain (documented order)

```
migrate_b313_graph_nodes.py     graph/nodes → nodes/
    ↓
generate_pipe_wall_graph_nodes.py   (optional content generation)
    ↓
inline_b313_node_assets.py        assets → inline source blocks
    ↓
merge_b313_node_sources.py        dual yaml+md → single yaml
    ↓
flatten_b313_nodes.py             nested paths → nodes/{node_id}/
    ↓
build_all_standards_dbs.py        refresh SQLite caches
```

Exact order used in production migration: **Unknown from static analysis** (inferred from docstrings and `docs/standards/*` only).

---

## Duplicate implementations

| Area | Implementations | Notes |
|------|-----------------|-------|
| Graph compilation | `build_graph_db.py` (`GraphBuilder` + `*_graph.db`) vs `build_standards_nodes_db.py` (`StandardsNodesDatabase` + `*_nodes.db`) | Both walk pack node sources; different DB schemas and consumers. |
| Table data sources | `build_standards_tables_db.py` (Python constants) vs `build_astm_standards_tables_db.py` (YAML seeds) vs pack `tables/*.yaml` fallback in `import_material_properties_pack` | B31.3 tables are not sourced from the same pipeline as ASTM. |
| Registry loading | `build_standards_registry_db._load_*_yaml` vs `engine.reference.*.load_*` registry helpers | Parallel parsing logic; registry script duplicates YAML load paths. |
| B31.3 node layout tools | `flatten_b313_nodes.py`, `inline_b313_node_assets.py`, `merge_b313_node_sources.py`, `migrate_b313_graph_nodes.py` | Sequential migration era; overlapping target pack `asme_b31.3`. |
| Material registry read | `load_material_registry()` in engine vs `_load_material_registry_yaml()` in registry build script | Same YAML file, two code paths. |

No recommendation on which to keep.

---

## Dead code (detail)

### `build_tasks` import in `build_all_standards_dbs.py`

- **Why unreachable in orchestrator**: `build_all()` never calls `build_tasks(...)`.
- **What may have used it**: Possibly planned step never added, or removed accidentally. **Unknown from static analysis.**
- **Confidence**: **High** that orchestrator skips tasks DB.

### `_collect_assets` in `build_standards_nodes_db.py`

- **Why unreachable**: Function body is `return []`; callers use `_collect_embedded_assets` only.
- **What may have used it**: Legacy disk-based asset scan before embedded-node model.
- **Confidence**: **High**

### B31.3 migration scripts (`migrate_*`, `flatten_*`, `inline_*`, `merge_*`)

- **Why unreachable**: No imports; docs describe completed migrations.
- **Confidence**: **High** for runtime; scripts remain for manual re-run.

### Unused imports in `build_standards_registry_db.py`

- `load_material_registry`, `load_supplemental_materials`, `load_pipe_dimensions_registry` imported but not referenced in module body.
- **Confidence**: **High**
