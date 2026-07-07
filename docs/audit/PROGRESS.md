# Architecture Audit Progress

Tracks folder-by-folder audit status per [Architecture Audit Mode](../todo/Architecture%20Audit%20Mode.md).

| Phase | Folder | Status | README |
|-------|--------|--------|--------|
| 0 | docs/audit/, .cursor/rules/ | done | this file |
| 1 | repo root | done | [ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md) |
| 1 | api/ | done | [api/README.md](../../api/README.md) |
| 1 | models/ | done | [models/README.md](../../models/README.md) |
| 1 | storage/ | done | [storage/README.md](../../storage/README.md) |
| 1 | engine/ | done | [engine/README.md](../../engine/README.md) |
| 1 | ai/ | done | [ai/README.md](../../ai/README.md) |
| 1 | desktopApp/ | done | [desktopApp/README.md](../../desktopApp/README.md) |
| 1 | dev/ | done | [dev/README.md](../../dev/README.md) |
| 1 | scripts/ | done | [scripts/README.md](../../scripts/README.md) |
| 1 | config/ | done | [config/README.md](../../config/README.md) |
| 2 | tests/ | done | [tests/README.md](../../tests/README.md) |
| 3a | knowledge/ restructure | done | — |
| 3b | knowledge/ path wiring | done | [engine/reference/knowledge_paths.py](../../engine/reference/knowledge_paths.py) |
| 3c | knowledge/ audit | done | [knowledge/README.md](../../knowledge/README.md) |
| 3d | knowledge/ folder flatten | done | ASTM single pack, flat units, workflows.db |
| 3e | knowledge/ stub cleanup | done | Removed api/, bpvc_section_viii, B31.3 reports/templates stubs |
| 3f | knowledge/ materials → global | done | `knowledge/global/materials/` registry + catalog |

## Cross-cutting

- [INDEX.md](INDEX.md) — master map of audit docs and section anchors
- [MAINTENANCE.md](MAINTENANCE.md) — living-doc workflow (update audit files when code changes)
- [DUPLICATES.md](DUPLICATES.md) — duplicate implementation register
- [EXECUTION_TRACES.md](EXECUTION_TRACES.md) — master execution traces

## Known gaps

- Full pytest after `knowledge/` move: **58 failures** (planner/graph/mvp/validation — standards graph behavior assertions). Path-resolution tests pass. Rebuild: `python scripts/build_all_standards_dbs.py`.
