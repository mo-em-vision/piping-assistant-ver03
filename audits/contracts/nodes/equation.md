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

One primary YAML file per equation. Node-owned execution metadata lives in the nested `execution` block in that file (not in separate sidecar files).

## 5. ID convention

| Variant        | `id` prefix                           | Notes                                     |
| -------------- | ------------------------------------- | ----------------------------------------- |
| Standards      | `asme-b313-`                          | Pack-scoped flat files                    |
| Unit transform | `EQ-unit-`                            | Requires `equation_class: transformation` |
| `key`          | Underscore form matching id semantics |                                           |
| Citation       | `equation_number`, `paragraph_number` | Required when id contains `-eq-`          |

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
| `applicability.applies_when` | Branch gating conditions (may also nest as `execution.applies_when`) |
| `validation` | Dimensional / authority checks |
| `edges` | `requires_parameter`, `calculates_parameter`, `depends_on_equation` |
| `execution` | Nested block for execution metadata: `variables`, `steps`, `outputs`, `display`, `applies_when`, `executor`, `execution_function`, `calculation_module`, `equation_id`, `paragraph` |

**Display rule:** equation input symbol names, descriptions, and units for preview/input tables resolve from each `requires[].parameter` → `PARAM-*` node. The inline `variables` block is for execution (SymPy steps, executor bindings) only — not a nomenclature or display source of truth.

## 9. Forbidden fields

```text
runtime_value, fact_value, user_input, execution_id, task_id,
calculation_result, selected_for_execution, active_in_context,
nomenclature_ref
```

Also forbidden:

- `authorized_by` in `edges` (use `authority.authorized_by`)
- `equation_class: lookup` or `validation`
- Top-level `links` block
- Structural edges (`parent`, `child`, `next`, `previous`)
- Node-owned sidecar files (`{id}.execution.yaml`, `{id}/execution.yaml`)

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `requires_parameter` | `PARAM-*` | Input binding |
| `calculates_parameter` | `PARAM-*` | Output binding |
| `depends_on_equation` | equation id | Execution ordering |
| Other taxonomy edges | per validator | Excluding `authorized_by` in edges |

## 11. Fields consumed by runtime components

**Canonical authoring:** The execution kernel reads `requires`, `calculates`, `expression`, and nested `execution` fields (`variables`, `steps`, `executor`, `display`, `applies_when`, etc.) from the primary equation YAML. Graph expansion reads branch gating from `applicability.applies_when` and/or `execution.applies_when`. Presentation reads `display` for equation blocks and resolves input symbol metadata from `requires` → `PARAM-*`. Paragraph citation chips use `paragraph_number` or `authority.authorized_by` on the equation node — not `nomenclature_ref`.

**Legacy runtime compatibility (read-only):** `engine/reference/equation_sidecar.py` may still merge metadata from old `{id}.execution.yaml` or `{id}/execution.yaml` files when present during pack load. This loader path is migration compatibility only — do not author, create, or maintain execution sidecars. Consolidate any remaining legacy files into the primary YAML `execution:` block.

## 12. Validation procedure

1. Parse YAML frontmatter from the primary equation file.
2. Run `validate_equation_node(meta)` from `engine/validation/equation_node_validator.py`.
3. Run `check_equation_frontmatter_placement(meta)` from `engine/reference/equation_authoring_policy.py` when validating execution-block placement.
4. Branch on id prefix: `asme-b313-*` vs `EQ-unit-*`.
5. Run `validate_authority_authorization` for standards equations.
6. Validate edges with `validate_edge_item(..., source_node_type="equation")`.
7. If legacy `{id}.execution.yaml` or `{id}/execution.yaml` files remain on disk, treat them as migration debt: consolidate into the primary YAML `execution:` block and confirm no duplicate or split authoring surfaces.
8. Rebuild graph DB and run equation-related pytest modules.

## 13. Common authoring mistakes

- Using `EQ-B313-*` legacy ids instead of `asme-b313-*` on disk.
- Omitting `authority.authority_context_required`.
- Putting `authorized_by` in `edges` instead of `authority` block.
- Missing `equation_number` when id contains `-eq-`.
- Embedding lookup or validation logic as equation class.
- Creating or retaining a separate `{id}.execution.yaml` or `{id}/execution.yaml` file instead of nesting execution metadata under `execution:` in the primary YAML.
- Duplicating execution fields across top level, nested `execution:`, and legacy sidecar files inconsistently.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3a.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-1-eq-2.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-302-3-5-eq-1a.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-pressure-design-thickness.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/equation_node_validator.py` — `validate_equation_node`, `_validate_standards_equation`, `_validate_unit_transformation_equation`
- Authority: `engine/validation/authority_authorization.py` — `validate_authority_authorization`
- Citation: `engine/reference/equation_metadata.py` — `equation_reference`
- Sidecar merge (legacy read-only at load): `engine/reference/equation_sidecar.py` — `merge_equation_sidecar_metadata` may read old execution sidecars; not an authoring surface
- Structural edges: `engine/validation/structural_edges.py`
