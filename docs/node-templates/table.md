# Table Node Template

Reference node for standards tables (not executable lookup).

```yaml
---
id: B313-table-A-1
type: table
title: Table A-1 Allowable Stress
table_id: asme_b31.3_A-1
standard: asme_b31.3

lookup_keys:
  - material
  - design_temperature

edges:
  - to: B313-lookup-allowable-stress
    type: outputs
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | Must be `table` |
| `table_id` | Compiled table identifier in standards DB |

## Optional fields

| Field | Description |
|-------|-------------|
| `lookup_keys` | Fields required to query this table |
| `standard` | Owning standard pack |
