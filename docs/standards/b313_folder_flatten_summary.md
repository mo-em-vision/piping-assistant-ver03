# B31.3 folder flatten — completion summary

**Date:** 2026-06-30  
**Scope:** ASME B31.3 pack only (`standards/asme/asme_b31.3/nodes/`). Node YAML/MD content unchanged.

## What changed

| Before | After |
|--------|-------|
| `nodes/304/304.1/304.1.1/` | `nodes/B313-304.1.1/` |
| `nodes/parameters/B313-param-P/` | `nodes/B313-param-P/` |
| `nodes/appendix_A/tables/B313-table-A-1/` | `nodes/B313-table-A-1/` |
| `nodes/302/302.3.5/B313-302.3.5/` | `nodes/B313-302.3.5/` |

- **48** primary node folders relocated to flat `nodes/{node_id}/` layout
- **10** redundant embedded-duplicate child folders removed (content remains in parent `source:` blocks)
- Asset subdirs (`equations/`, `conditions/`, `tables/`, etc.) moved with each parent

## What did not change

- Node IDs (`B313-*`) and graph edges
- Equation formulas, nomenclature prose, or YAML/MD node content
- ASTM, units, and other packs (already flat)

## Tooling

| Script / module | Role |
|-----------------|------|
| `scripts/flatten_b313_nodes.py` | Migration (dry-run supported) |
| `scripts/build_all_standards_dbs.py` | Rebuild `source_rel_path` in SQLite caches |
| `engine/reference/standards_markdown.py` | Dual yaml/md merge; column-0 frontmatter delimiter fix |
| `engine/reference/standards_reader.py` | Direct flat path resolution (removed `/304.1/` shims) |
| `scripts/build_standards_nodes_db.py` | Flat-path dedup; embedded-node alias rules |
| `api/dev_studio/node_repository.py` | New nodes default to `nodes/{node_id}/` |

## Verification

```bash
python scripts/build_all_standards_dbs.py
python -m pytest tests/reference tests/executor/test_mawp_calculation.py tests/storage/test_standards_tables.py tests/api/test_standards_browse.py tests/api/test_dev_studio_crud.py
python -m pytest tests/api tests/mvp/test_desktop_mvp_workflow.py
```

All targeted suites pass after rebuild.

## Single-file merge (2026-06-30)

Dual `node.yaml` + `node.md` pairs for `B313-304.1.1`, `B313-304.1.2`, `B313-304.1.3`, and `B313-MAWP-SECTION` were consolidated into one `node.yaml` per folder via `scripts/merge_b313_node_sources.py`. Node Dev Studio and loaders prefer `node.yaml` when resolving paths.

## Browse UX

Pack navigation (`index.md`) still groups nodes by standard section. The standards browse API adds synthetic **Tables** subgroups for flat table/lookup nodes where folder depth no longer implies grouping.
