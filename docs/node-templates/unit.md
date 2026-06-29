# Unit Node Template

Global unit ontology nodes live in `standards/units/nodes/`. They are shared across all standards packs.

```yaml
---
id: UNIT-psi
type: unit
symbol: psi
dimension: pressure
aliases:
  - PSI
description: Pounds per square inch

converts_to:
  - node_id: UNIT-Pa
    factor: 6894.757293168
---
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique id with `UNIT-` prefix |
| `type` | Must be `unit` |
| `symbol` | Short symbol used in UI and legacy `unit` fields |
| `dimension` | Quantity kind: `pressure`, `length`, `temperature`, `dimensionless` |

## Optional fields

| Field | Description |
|-------|-------------|
| `aliases` | Alternate spellings (`f`, `degF`, etc.) |
| `description` | Human-readable name |
| `converts_to` | List of target unit nodes with conversion metadata |
| `display` | Explorer / Dev Studio styling (see parameter template) |

## converts_to metadata

| Field | Description |
|-------|-------------|
| `node_id` | Target unit node id |
| `factor` | Multiplier applied to the source value |
| `offset` | Added after multiply (affine transforms, e.g. °F → K) |

Conversion formula: `target = source * factor + offset` (default `offset: 0`).

## Canonical SI units

| Dimension | Canonical node |
|-----------|----------------|
| pressure | `UNIT-Pa` |
| length | `UNIT-mm` |
| temperature | `UNIT-K` |
| dimensionless | `UNIT-dimensionless` |

Parameters reference units via `canonical_unit: UNIT-Pa`, not inline `unit:` strings.
