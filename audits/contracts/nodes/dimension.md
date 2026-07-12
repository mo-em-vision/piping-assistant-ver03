# Dimension Node Contract

## 1. Purpose

A dimension node defines a measurable or semantic category (pressure, length, dimensionless) used to determine unit compatibility for parameters, facts, and equations.

## 2. Use this node when

- You are declaring a physical dimension with a canonical unit and allowed units list.
- Parameters need `DIM-*` references for dimensional analysis.
- You need `dimensionless` or `categorical` semantic dimensions without physical units.

## 3. Do not use this node when

- You need a specific measurement symbol (use `unit`).
- You need a gatherable engineering field (use `parameter`).
- You need a broad semantic concept grouping (use `concept`).

## 4. File location

`knowledge/global/dimensions/nodes/DIM-{slug}.yaml`

## 5. ID convention

| Field | Rule |
| --- | --- |
| `id` | `DIM-{kebab-case}` (e.g. `DIM-pressure`) |
| `key` | Underscore machine key (`pressure`) |
| `dimension_kind` | `physical`, `dimensionless`, or `categorical` |
| `canonical_unit` | `UNIT-*` for physical dimensions; absent/null for categorical |

## 6. Copyable minimal YAML skeleton

Physical dimension:

```yaml
---
id: DIM-pressure
type: dimension
key: pressure
name: Pressure
dimension_kind: physical
canonical_unit: UNIT-Pa
description: Force per unit area.
edges:
  - type: allows_unit
    target: UNIT-Pa
  - type: allows_unit
    target: UNIT-psi
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

Dimensionless:

```yaml
---
id: DIM-dimensionless
type: dimension
key: dimensionless
name: Dimensionless
dimension_kind: dimensionless
description: Ratios and factors without physical dimension.
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Starts with `DIM-` |
| `type` | `dimension` |
| `key` | Machine key |
| `name` | Human-readable name |
| `dimension_kind` | `physical`, `dimensionless`, or `categorical` |
| `description` | Definition |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |

For `dimension_kind: physical`: `canonical_unit` (`UNIT-*`) and at least one `allows_unit` edge including the canonical unit.

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `aliases` | Synonyms (`stress` for pressure dimension) |
| `canonical_unit` | Reference unit for conversions |
| `edges` | `allows_unit` → `UNIT-*` |
| `metadata.status` | Lifecycle |

## 9. Forbidden fields

```text
runtime_value, fact_value, user_input, value, factor, offset
```

Also forbidden:

- Top-level `links` block
- Inline conversion formulas (belong on `unit` / `EQ-unit-*`)

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `allows_unit` | `UNIT-*` | Preferred over generic `references` |
| `specializes` / `generalizes` | `DIM-*` | Optional ontology hierarchy |
| Other taxonomy edges | per validator | |

Parameters link back via `has_dimension` edges.

## 11. Fields consumed by runtime components

Nomenclature resolver loads dimension nodes to validate parameter unit compatibility. Unit resolver uses `canonical_unit` and `allows_unit` lists. Equation validation checks `requires`/`calculates` dimension fields against `DIM-*`. Graph queries use `dimension_allowed_unit_ids` for allowed unit sets.

## 12. Validation procedure

No dedicated `dimension_node_validator.py`. Validate via:

1. Confirm required fields and revision metadata.
2. Run `tests/units/test_physical_dimensions.py` — checks `dimension_kind`, `canonical_unit`, and `allows_unit` targets exist.
3. Confirm every `allows_unit` target is an existing `UNIT-*` file.
4. For categorical dimensions, confirm no canonical unit and empty allowed units.

## 13. Common authoring mistakes

- Omitting `allows_unit` edges for physical dimensions.
- `canonical_unit` not included in own `allows_unit` list.
- Using `references` instead of `allows_unit`.
- Putting conversion factors on the dimension node.
- Using `DIM-*` for material designations (use `DIM-material-designation` with `dimension_kind: categorical`).

## 14. Current repository examples

- `knowledge/global/dimensions/nodes/DIM-pressure.yaml`
- `knowledge/global/dimensions/nodes/DIM-length.yaml`
- `knowledge/global/dimensions/nodes/DIM-temperature.yaml`
- `knowledge/global/dimensions/nodes/DIM-dimensionless.yaml`

## 15. Implementation evidence appendix

- Tests: `tests/units/test_physical_dimensions.py` — `test_physical_dimension_nodes_reference_existing_units`
- Allowed units query: `engine/reference/graph_edge_schema.py` — `dimension_allowed_unit_ids`
- Nomenclature: `engine/reference/nomenclature_resolver.py` — `_load_dimension_node`
- Parameter binding: `engine/reference/parameter_metadata.py`
