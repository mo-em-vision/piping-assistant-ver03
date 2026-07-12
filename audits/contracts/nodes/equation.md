# Equation Node Contract

## 1. Purpose

An equation node defines a deterministic calculation that consumes input parameters and produces output parameters through an executable formula or function.

## 2. Use this node when

- You are modeling a standards formula (e.g. ASME B31.3 eq. 3a).
- You need unit transformation between two `UNIT-*` nodes (`EQ-unit-*`).
- Inputs and outputs bind to `PARAM-*` nodes via `requires` and `calculates`.

## 3. Do not use this node when

- You need table lookup resolution (use `lookup`).
- You need pass/fail validation only (use `validation_rule`).
- You need to store calculated numeric results (runtime Facts).
- `equation_class` would be `lookup` or `validation` (wrong node type).

## 4. File location

| Variant | Path |
| --- | --- |
| Standards pack equations | `knowledge/standards/<pack>/nodes/equation/asme-b313-*.yaml` |
| Unit transformation | `knowledge/global/units/nodes/EQ-unit-*.yaml` or adjacent equation folder |
| Optional execution sidecar | `{id}.execution.yaml` or `{id}/execution.yaml` |

## 5. ID convention

| Variant | `id` prefix | Notes |
| --- | --- | --- |
| Standards | `asme-b313-` | Pack-scoped flat files |
| Unit transform | `EQ-unit-` | Requires `equation_class: transformation` |
| `key` | Underscore form matching id semantics | |
| Citation | `equation_number`, `paragraph_number` | Required when id contains `-eq-` |

## 6. Copyable minimal YAML skeleton

Standards equation:

```yaml
---
id: asme-b313-304-1-2-eq-3a
type: equation
key: asme-b313-304-1-2-eq-3a
name: Example Wall Thickness Equation
equation_class: calculation
calculation_kind: algebraic
description: Example pressure design thickness calculation.
equation_number: 3a
paragraph_number: 304.1.2-a
authority:
  authorized_by:
    - 304.1.2-a
  authority_context_required: true
requires:
  - symbol: P
    parameter: PARAM-internal-design-gage-pressure
calculates:
  - symbol: t
    parameter: PARAM-required-wall-thickness
metadata:
  status: active
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

### Standards (`asme-b313-*`)

| Field | Rule |
| --- | --- |
| `id` | Starts with `asme-b313-` |
| `type` | `equation` |
| `key`, `name`, `description` | Non-empty |
| `equation_class` | `calculation`, `aggregation`, or `transformation` |
| `authority.authorized_by` | Non-empty paragraph id list |
| `authority.authority_context_required` | Boolean |
| `requires` and/or `calculates` | At least one non-empty list |
| `metadata.status` | e.g. `active`, `draft` |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |
| `equation_number` | When id contains `-eq-` |

For `calculation_kind: function`, either `executor` or `expression.formula` is required.

### Unit transformation (`EQ-unit-*`)

| Field | Rule |
| --- | --- |
| `id` | Starts with `EQ-unit-` |
| `equation_class` | `transformation` |
| `conversion.from_unit`, `conversion.to_unit` | `UNIT-*` ids |
| `expression.formula` | Non-empty |
| `requires`, `calculates` | Non-empty lists with `symbol` and `unit` (`UNIT-*`) |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `calculation_kind` | `algebraic`, `piecewise`, `conditional`, `iterative`, `function` |
| `display.latex`, `display.text` | Rendered equation form |
| `expression.language`, `expression.formula` | Sympy or other executor input |
| `executor`, `execution_function`, `calculation_module` | Function-based execution |
| `applicability.applies_when` | Branch gating conditions |
| `validation` | Dimensional / authority checks |
| `edges` | `requires_parameter`, `calculates_parameter`, `depends_on_equation` |
| Sidecar execution keys | `variables`, `steps`, `outputs`, `nomenclature_ref`, etc. |

## 9. Forbidden fields

```text
runtime_value, fact_value, user_input, execution_id, task_id,
calculation_result, selected_for_execution, active_in_context
```

Also forbidden:

- `authorized_by` in `edges` (use `authority.authorized_by`)
- `equation_class: lookup` or `validation`
- Top-level `links` block
- Structural edges (`parent`, `child`, `next`, `previous`)

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `requires_parameter` | `PARAM-*` | Input binding |
| `calculates_parameter` | `PARAM-*` | Output binding |
| `depends_on_equation` | equation id | Execution ordering |
| Other taxonomy edges | per validator | Excluding `authorized_by` in edges |

## 11. Fields consumed by runtime components

Execution kernel reads `requires`, `calculates`, `expression`, `executor`, and sidecar `steps` to evaluate formulas. Graph expansion reads `applicability.applies_when` to include or exclude equations. Presentation reads `display` for equation blocks. Validation engine may read `validation` metadata before execution. Nomenclature resolver uses `nomenclature_ref` for symbol tables.

## 12. Validation procedure

1. Parse YAML frontmatter (and merge execution sidecar if present).
2. Run `validate_equation_node(meta)` from `engine/validation/equation_node_validator.py`.
3. Branch on id prefix: `asme-b313-*` vs `EQ-unit-*`.
4. Run `validate_authority_authorization` for standards equations.
5. Validate edges with `validate_edge_item(..., source_node_type="equation")`.
6. Rebuild graph DB and run equation-related pytest modules.

## 13. Common authoring mistakes

- Using `EQ-B313-*` legacy ids instead of `asme-b313-*` on disk.
- Omitting `authority.authority_context_required`.
- Putting `authorized_by` in `edges` instead of `authority` block.
- Missing `equation_number` when id contains `-eq-`.
- Embedding lookup or validation logic as equation class.
- Duplicating execution fields in frontmatter and sidecar inconsistently.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3a.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-1-eq-2.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-302-3-5-eq-1a.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-pressure-design-thickness.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/equation_node_validator.py` — `validate_equation_node`, `_validate_standards_equation`, `_validate_unit_transformation_equation`
- Authority: `engine/validation/authority_authorization.py` — `validate_authority_authorization`
- Citation: `engine/reference/equation_metadata.py` — `equation_reference`
- Sidecar: `engine/reference/equation_sidecar.py` — `merge_equation_sidecar_metadata`, `_EXECUTION_KEYS`
- Structural edges: `engine/validation/structural_edges.py`
