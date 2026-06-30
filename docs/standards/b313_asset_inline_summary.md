# B31.3 Asset Inline Migration Summary

Migration completed June 2026. Per-node asset subfolders under ASME B31.3 flat nodes were removed; content was inlined into parent `node.yaml` as embedded `source:` blocks.

## Nodes simplified (asset subfolders removed)

| Node | Before | After |
|------|--------|-------|
| `B313-304.1.2` | `equations/`, `conditions/`, `notes/`, `references/` | `node.yaml` only |
| `B313-304.1.1` | `equations/` | `node.yaml` only |
| `B313-302.3.5` | `node.md` + `equations/` (md + py) | `node.yaml` + `eq_1a_*.py`, `eq_1b_*.py`, `eq_1c_*.py` at root |
| `B313-304.3.3` | `node.md` + `equations/` | `node.yaml` only |
| `B313-MAWP-SECTION` | `equations/` | `node.yaml` only |
| `B313-MAWP-CALCULATION` | `equations/` ref | `node.yaml` only |

Legacy nested trees under `nodes/302/`, `nodes/304/`, and `nodes/parameters/` were removed after flat migration.

## Disk files inlined or deleted

- `B313-304.1.2`: `wall_thickness.md`, `mawp_pressure.md`, `thick_wall_y.md`, `thin_wall_check.md`, corrosion/mill notes, `material_stress.md` reference → embedded `source:` on metadata entries
- `B313-304.1.1`: `eq_2_minimum_required_thickness.md` → subsection `equations[].source`
- `B313-302.3.5`: three equation `.md` files → `equations[].source`; `.py` modules moved to node root
- `B313-304.3.3`: four reinforcement equation `.md` files → `equations[].source`
- `B313-MAWP-SECTION`: `pressure_design_thickness.md` → embedded `source:`

## Cross-node path updates

| Old path | Updated |
|----------|---------|
| `../304.1.2/equations/mawp_pressure.md` | `nodes/B313-304.1.2/equations/mawp_pressure.md` (alias → embedded source) |
| `../304.1.2/equations/thick_wall_y.md` | `nodes/B313-304.1.2/equations/thick_wall_y.md` |
| `../mawp_definition/equations/pressure_design_thickness.md` | `nodes/B313-MAWP-SECTION/equations/pressure_design_thickness.md` |
| `B313-MAWP-DEFINITION` (legacy id) | Resolves to `B313-MAWP-SECTION` via `LEGACY_NODE_ID_ALIASES` |

Duplicate `file:` keys were removed where a matching `source:` block already existed.

## Restored metadata lost during merge

- `B313-304.1.1`: `depends_on` (conditional calculation paths for internal/external pressure), `assumptions`, `interactions`
- `B313-304.1.2`: `interactions`, `inputs` (from legacy `304/304.1/304.1.2/node.md`)
- `B313-interaction-pressure-loading`: flat `node.yaml` recreated for workflow `contains` edge

## Loader and executor changes

- `StandardsReader.read_asset_text` — embedded-first; synthetic aliases when `file:` removed
- `scripts/build_standards_nodes_db.py` — `_collect_embedded_assets`; no disk `_ASSET_DIRS` scan
- `engine/executor/calculation_engine.py` — `execute_from_text`
- `engine/executor/formula_loader.py` — embedded / cross-node formula resolution
- `engine/executor/node_runner.py` — skip contained equations without `sympy`; fix micro-lookup temperature units
- `engine/graph/lazy_expander.py` — expand conditional `depends_on`, lookup output producers, execution ordering
- `api/node_display.py` — render equations from embedded `source:` (no `file:` required)

## Verification

```bash
python scripts/build_all_standards_dbs.py
python -m pytest tests/reference tests/executor tests/calculation tests/api tests/mvp/test_desktop_mvp_workflow.py
```

Result: **265 passed**, 2 skipped.

Graph edges, planner workflow selection, and report structure are unchanged. Node IDs and graph relationships were preserved.
