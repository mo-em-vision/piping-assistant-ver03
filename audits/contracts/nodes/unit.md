# Unit Node Contract

## 1. Purpose

A unit node defines a measurement unit, its display symbol, dimension membership, and deterministic conversion to the canonical unit of that dimension (or via `EQ-unit-*` equations).

## 2. Use this node when

- You are adding a unit symbol (`psi`, `mm`, `degC`) to the global unit ontology.
- Parameters and equations need `UNIT-*` references for dimensional checking.
- Non-linear conversions require a `converts_to` edge with `equation: EQ-unit-*`.

## 3. Do not use this node when

- You need a dimension category itself (use `dimension`).
- You need to store a numeric value with a unit (runtime Fact with unit).
- You need a formula unrelated to unit conversion (use standards `equation`).

## 4. File location

`knowledge/global/units/nodes/UNIT-{symbol}.yaml`

Unit transformation equations: `knowledge/global/units/nodes/EQ-unit-*.yaml` (validated with equation contract).

## 5. ID convention

| Field | Rule |
| --- | --- |
| `id` | `UNIT-{symbol}` (e.g. `UNIT-psi`, `UNIT-mm`) |
| `symbol` | Display symbol (e.g. `psi`) |
| `dimension` | `DIM-*` parent reference |
| Canonical self-reference | `conversion.target` equals own `id` with `factor: 1`, `offset: 0` |

## 6. Copyable minimal YAML skeleton

Canonical unit (dimension anchor):

```yaml
---
id: UNIT-Pa
type: unit
symbol: Pa
name: Pascal
dimension: DIM-pressure
description: SI unit of pressure.
conversion:
  target: UNIT-Pa
  factor: 1
  offset: 0
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

Non-canonical unit with `converts_to` edge:

```yaml
---
id: UNIT-psi
type: unit
symbol: psi
name: Pound per Square Inch
dimension: DIM-pressure
description: Pressure unit equal to one pound-force per square inch.
conversion:
  target: UNIT-Pa
  factor: 6894.757293168
  offset: 0
edges:
  - type: belongs_to_dimension
    target: DIM-pressure
  - type: converts_to
    target: UNIT-Pa
    factor: 6894.757293168
    offset: 0
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Starts with `UNIT-` |
| `type` | `unit` |
| `symbol` | Non-empty display symbol |
| `dimension` | Starts with `DIM-` |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |
| Conversion path | Canonical `conversion.target` = self, **or** at least one `converts_to` edge |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `name` | Human-readable unit name |
| `description` | Definition |
| `aliases` | Synonyms (`PSI`, `lb/in2`) |
| `conversion.target`, `factor`, `offset` | Inline scaling to canonical |
| `edges` | `belongs_to_dimension`, `converts_to` |
| `metadata.status` | Lifecycle |

### `converts_to` edge rules

- Target must be `UNIT-*`.
- Specify `factor` **or** `equation` (not both).
- Non-zero `offset` requires `equation`, not bare `factor`.

## 9. Forbidden fields

```text
runtime_value, fact_value, user_input, value (numeric instance)
```

Also forbidden:

- Top-level `links` block
- Both `factor` and `equation` on the same `converts_to` edge

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `belongs_to_dimension` | `DIM-*` | Dimension membership |
| `converts_to` | `UNIT-*` | With `factor` or `equation` |
| Other taxonomy edges | per validator | Non-`converts_to` edges validated separately |

## 11. Fields consumed by runtime components

Unit resolver reads `conversion` and `converts_to` edges to convert Fact values between units. Equation dimensional checks validate `requires`/`calculates` unit fields against `UNIT-*`. Parameter `metadata.canonical_unit` resolves through unit nodes. Dimension nodes aggregate allowed units via `allows_unit` edges.

## 12. Validation procedure

1. Parse YAML frontmatter.
2. Run `validate_unit_node(meta, known_nodes=...)` from `engine/validation/unit_node_validator.py`.
3. For pack-wide checks, run `validate_unit_pack(nodes)`.
4. When referencing `EQ-unit-*` on edges, confirm equation `conversion.from_unit` / `to_unit` match.
5. Run `python -m pytest tests/units -q`.

## 13. Common authoring mistakes

- Non-canonical unit without `converts_to` edge or canonical self-`conversion`.
- Using both `factor` and `equation` on one `converts_to` edge.
- Non-zero `offset` with factor-only conversion (use `EQ-unit-*`).
- `dimension` not matching the `belongs_to_dimension` edge target.
- Referencing unknown `EQ-unit-*` equation on `converts_to`.

## 14. Current repository examples

- `knowledge/global/units/nodes/UNIT-psi.yaml`
- `knowledge/global/units/nodes/UNIT-Pa.yaml`
- `knowledge/global/units/nodes/UNIT-mm.yaml`
- `knowledge/global/units/nodes/UNIT-degC.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/unit_node_validator.py` — `validate_unit_node`, `validate_unit_pack`, `_validate_converts_to_edge`
- Equation (unit transform): `engine/validation/equation_node_validator.py` — `_validate_unit_transformation_equation`
- Resolver: `engine/units/unit_resolver.py` — `UnitResolver`
- Tests: `tests/units/test_physical_dimensions.py`
