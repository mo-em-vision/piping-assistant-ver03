# Table Node Template

Reference node for standards tables (lookup nodes under `nodes/tables/`).

```yaml
---
id: B313-table-A-1
standard: asme_b31.3
source:
  pack: asme_b31.3
  yaml: nodes/tables/B313-table-A-1.yaml
  tables_db: asme_b313_tables.db
  table_id: asme_b31.3_A-1
type: lookup
title: Table A-1 — Allowable Stress
version: '1.0'
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id (`B313-table-*` for B31.3 tables) |
| `type` | Must be `lookup` |
| `standard` | Owning standard pack slug |
| `source.table_id` | Compiled table identifier in standards DB (unchanged SQLite id) |
| `source.tables_db` | Pack tables database filename |
| `source.yaml` | Relative path to this YAML within the pack |

## Optional fields

| Field | Description |
|-------|-------------|
| `lookup_keys` / `inputs` | Fields required to query this table |
| `outputs` | Result fields produced by lookup |
| `paragraph` | Standards paragraph reference |

## Notes

- Graph node ids use the `B313-table-*` prefix; SQLite `table_id` values remain `asme_b31.3_*`.
- Legacy `table-*` ids resolve via `b313_legacy_aliases.py`.
- B36.10 pipe dimension tables use `B3610-table-*` ids with `registry` metadata instead of `source.tables_db`.
