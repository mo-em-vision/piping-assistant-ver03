# Validation Rule Node Contract

## 1. Purpose

A validation rule node defines a deterministic pass/fail check, applicability gate, or limit check against input parameters without producing calculated engineering quantities.

## 2. Use this node when

- A standard imposes a geometry limit (e.g. thin-wall check `t < D/6`).
- You need to validate applicability before or after an equation runs.
- Output is a boolean or status parameter (`PARAM-thin-wall-applicability`).

## 3. Do not use this node when

- You need to compute a numeric design value (use `equation`).
- You need table interpolation (use `lookup`).
- You need to store the validation outcome for a specific task (runtime validation result).

## 4. File location

`knowledge/standards/<pack>/nodes/validation_rule/{id}.yaml`

Ids typically follow `asme-b313-{section}-valrule-{suffix}.yaml`.

## 5. ID convention

| Pattern | Example |
| --- | --- |
| Pack-scoped | `asme-b313-304-1-2-valrule-a` |
| `VALRULE-*` prefix | Allowed for descriptive global ids |
| `key` | Matches id semantics in underscore form |
| `rule_class` | Must be `validation` when set |

## 6. Copyable minimal YAML skeleton

```yaml
---
id: asme-b313-304-1-2-valrule-a
type: validation_rule
key: asme-b313-304-1-2-valrule-a
name: Thin-Wall Applicability
rule_class: validation
description: Verify t < D/6 for thin-wall equation applicability.
authority:
  authorized_by:
    - 304.1.2-a
  authority_context_required: true
requires:
  - symbol: t
    parameter: PARAM-required-wall-thickness
  - symbol: D
    parameter: PARAM-outside-diameter
validates:
  - parameter: PARAM-thin-wall-applicability
metadata:
  status: active
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `type` | `validation_rule` |
| `key`, `name`, `description` | Non-empty |
| `validates` list or `validates_parameter` edge | At least one output check |
| `authority.authorized_by` | Non-empty paragraph id list |
| `authority.authority_context_required` | Boolean |
| `metadata.status` | When metadata block is present |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `display.text` | Human-readable check expression |
| `expression.language`, `expression.formula` | Executable check |
| `requires` | Input parameter bindings |
| `conditions` | Structured condition blocks |
| `on_fail` | `severity`, `blocks_goal`, `message`, `creates_warning` |
| `edges` | `requires_parameter`, `validates_parameter`, `constrains_equation` |
| Sidecar execution keys | Same loader as equations (`expression`, `steps`, etc.) |

## 9. Forbidden fields

```text
runtime_value, fact_value, user_input, execution_id, task_id,
calculation_result, selected_for_execution, active_in_context
```

Also forbidden:

- `authorized_by` in `edges`
- `calculates_parameter` edges (use `validates_parameter`)
- `rule_class` other than `validation`
- Top-level `links` block
- Structural edges

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `requires_parameter` | `PARAM-*` | Inputs to check |
| `validates_parameter` | `PARAM-*` | Check outcome parameter |
| `constrains_equation` | equation id | Equation applicability link |
| `creates_warning` | `TEXT-*` / text id | Warning on failure |
| Other taxonomy edges | per validator | Excluding `authorized_by` in edges |

## 11. Fields consumed by runtime components

Validation engine evaluates `expression`, `conditions`, and `requires` against current Facts. Graph expansion includes rules on active paths. Planner may schedule validation goals for `validates` parameters. Presentation reads `display` and `on_fail.message` for warning blocks.

## 12. Validation procedure

Dedicated validator: `engine/validation/validation_rule_node_validator.py`.

Audit projection:

```bash
python scripts/audit_current_node_yaml.py --filter validation_rule
```

Report: `audits/reports/nodes/validation-rule-node-audit.md`.

Checks:

1. Parse YAML frontmatter (merge equation sidecar when shared execution file is present).
2. Run `validate_validation_rule_node(meta)`.
3. Run `validate_authority_authorization(meta, node_type="validation_rule")`.
4. Confirm `validates` or `validates_parameter` edge exists.
5. Validate edges; reject `calculates_parameter` and structural edges.
6. Run `tests/reference/test_validation_rule_ontology.py` and `tests/reference/test_validation_rule_audit_process.py`.

## 13. Common authoring mistakes

- Using an equation node for a simple inequality check.
- Omitting `authority.authority_context_required`.
- Using `calculates_parameter` instead of `validates_parameter`.
- Putting `authorized_by` in `edges`.
- Setting `rule_class` to something other than `validation`.
- Missing `metadata.status` when other metadata fields are present.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-2-valrule-a.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-2-valrule-b.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-1-valrule-a.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-3-3-valrule-6a.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/validation_rule_node_validator.py` — `validate_validation_rule_node`; audit `--filter validation_rule` → `audits/reports/nodes/validation-rule-node-audit.md`
- Tests: `tests/reference/test_validation_rule_ontology.py`, `tests/reference/test_validation_rule_audit_process.py`
- Authority: `engine/validation/authority_authorization.py` — `validate_authority_authorization`
- Sidecar merge (shared with equation): `engine/reference/equation_sidecar.py` — `merge_equation_sidecar_metadata`
- Structural edges: `engine/validation/structural_edges.py`
