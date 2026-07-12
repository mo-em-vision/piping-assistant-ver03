# Dimension Node YAML Audit

**Overall status:** PASS

_Filtered projection aligned with `audits/contracts/nodes/dimension.md`._

## Summary

- Dimension files inspected: 6
- Passing: 6
- Warnings: 0
- Failing: 0

## Enforcement policy

- Validator: `engine/validation/dimension_node_validator.py`.
- Physical/dimensionless: `canonical_unit` and `allows_unit` edges must reference existing `UNIT-*` nodes.
- Categorical: no `canonical_unit` and no `allows_unit` edges.
- Supplementary test: `tests/units/test_physical_dimensions.py`.

---

## Dimension node inventory

| YAML file | Node ID | Validator | Result | Problems |
| --- | --- | --- | --- | --- |
| `knowledge/global/dimensions/nodes/DIM-dimensionless.yaml` | `DIM-dimensionless` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-length.yaml` | `DIM-length` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-material-designation.yaml` | `DIM-material-designation` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-pressure.yaml` | `DIM-pressure` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-temperature.yaml` | `DIM-temperature` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-velocity.yaml` | `DIM-velocity` | `validate_dimension_node` | **PASS** | — |
