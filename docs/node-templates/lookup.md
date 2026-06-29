# Lookup Node Template

Executable table resolution triggered during graph traversal.

```yaml
---
id: B313-lookup-allowable-stress
type: lookup
title: Allowable stress lookup
table_id: asme_b31.3_A-1
output_param: B313-param-S

keys:
  - material
  - design_temperature

interpolation: true

edges:
  - to: B313-table-A-1
    type: uses_table
  - to: B313-param-S
    type: outputs
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | Must be `lookup` |
| `table_id` | Compiled table identifier |
| `output_param` | Parameter node id receiving the lookup result |
| `keys` | Input fields required for lookup |

## Optional fields

| Field | Description |
|-------|-------------|
| `interpolation` | Enable temperature interpolation |
| `subsection` | Table subsection selector |
