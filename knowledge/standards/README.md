# Standards packs

Per-standard engineering knowledge packs grouped by issuing body.

## Purpose

Self-contained standards content: graph nodes, lookup tables, workflow roots, and compiled SQLite caches.

## Groups and packs

| Group | Pack | Workflow roots | Notes |
|-------|------|----------------|-------|
| **asme/** | `asme_b31.3` | `WF-PIPE-WALL-THICKNESS`, `WF-MAWP` | Primary MVP standard |
| | `asme_b36.10` | — | Pipe NPS/OD/schedule dimensions |
| **astm/** | `astm` (consolidated) | — | Material nodes (`nodes/A*.yaml`) and per-spec table DBs at pack root |

## Cross-pack indexes

| Path | Role |
|------|------|
| `workflows.db` (built) | Compiled workflow nodes from `{pack}/nodes/workflows/*.yaml` |
| `standards_config.db` (built) | Merged registry of materials, dimensions, packs |

Material registry and search catalog live under [`knowledge/global/materials/`](../global/materials/) (not inside `standards/`).

## Entry Points

| Path | Role |
|------|------|
| `{group}/{pack}/index.md` | Pack manifest |
| `engine/reference/standards_paths.py` | `resolve_standard_pack()`, `list_standard_packs()` |

## Dependencies

**Resolver:** `engine/reference/standards_paths.py` — `STANDARD_GROUPS = ("asme", "astm")`. ASTM material slugs (`astm_a53`, `astm_a106`, …) alias to the single `astm` pack.

**Global registries:** `knowledge/global/dimensions/registry.yaml` references dimension packs here.

## Runtime Usage

**On execution path:** yes — all active tasks load a pack via `StandardsReader(standards_root, standard=...)`.

## Notes

- Each pack: `nodes/`, `tables/` (optional), `nodes/workflows/` (workflow YAML), `*_graph.db`, `*_nodes.db`, `*_tables.db`.
- Report templates live in `engine/reports/templates/`, not under standard packs.
- Pack resolution slug: `asme_b31.3` (not full path).

## Compile commands

```bash
python scripts/build_all_standards_dbs.py
python scripts/build_standards_tasks_db.py
python scripts/build_graph_db.py asme_b31.3
```
