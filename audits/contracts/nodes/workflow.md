# Workflow Node Contract

## 1. Purpose

A workflow node defines a reusable engineering objective — what kind of task it is, which authorities and parameters may participate, and how goals expand — without executing calculations or storing runtime state.

## 2. Use this node when

- You are defining an end-to-end engineering task (pipe wall thickness design, MAWP).
- You need goal templates, entry paragraphs, and expected parameter sets.
- Navigation phase order and gate fields belong in a runtime sidecar.

## 3. Do not use this node when

- You need a single formula (use `equation`).
- You need to store the current workflow phase or user inputs (runtime task state).
- You are modeling standard paragraph text (use `paragraph`).

## 4. File location

`workflows/{machine-key}.yaml` (e.g. `pipe-wall-thickness.yaml`)

One primary YAML file per workflow. Deterministic runtime metadata (`navigation`, `interactions`, `texts`, etc.) lives in the nested `runtime` block in that file.

## 5. ID convention

| Field | Rule |
| --- | --- |
| `id` | `WF-{UPPER-KEBAB}` (e.g. `WF-PIPE-WALL-THICKNESS`) |
| `key` | Snake-case machine key (e.g. `pipe_wall_thickness_design`) |
| `workflow_class` | One of allowed classes (section 8) |
| Legacy aliases | `B313-WF-*` resolved at runtime only — do not author as primary id |

## 6. Copyable minimal YAML skeleton

```yaml
---
id: WF-EXAMPLE
type: workflow
key: example_workflow
name: Example Workflow
workflow_class: design_calculation
description: >
  Example engineering workflow objective defined for graph expansion.
runtime:
  navigation:
    assumption_gate_fields: []
    phases: {}
metadata:
  status: draft
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Starts with `WF-` |
| `type` | `workflow` |
| `key` | Machine key |
| `name` | Human-readable title |
| `workflow_class` | Allowed class (section 8) |
| `description` | Non-empty |
| `metadata.status` | e.g. `draft`, `active` |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `domain` | Engineering domain tags |
| `expected_authorities` | `AUTH-*` list |
| `entry_points` | Paragraph anchors with `role` |
| `expected_parameters` | Anticipated `PARAM-*` list |
| `goal_expansion` | Root and child goal templates |
| `applicability.applies_to` | `CONCEPT-*` filters |
| `report` | Report section requirements |
| `phases` | Synthesized navigation when no sidecar |
| `edges` | `starts_from_paragraph`, `may_use_equation`, `next`, etc. |

### Allowed `workflow_class` values

```text
design_calculation, verification, inspection, assessment, lookup,
selection, reporting, screening, troubleshooting
```

Runtime-only fields belong in `workflows/{WF-ID}/runtime.yaml` — see [sidecars/workflow-runtime.md](sidecars/workflow-runtime.md).

## 9. Forbidden fields

Forbidden in **frontmatter** (must be in runtime sidecar):

```text
navigation, assumptions, interactions, inputs, equations,
nomenclature, conditions, provisional_assumptions, engineering_intent,
slug, goal_output, purpose, title, documentation, texts,
suggested_workflows
```

Also forbidden:

```text
runtime_value, fact_value, user_input, execution_id, task_id,
calculation_result, runtime_result, current_phase, active_goal_id
```

- Top-level `links` block

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `starts_from_paragraph` | paragraph id | Primary anchor |
| `may_use_equation` | equation id | Participating equations |
| `may_use_lookup` | lookup id | Participating lookups |
| `may_use_validation_rule` | validation rule id | Participating checks |
| `requires_parameter` | `PARAM-*` | Expected inputs |
| `may_create_goal` | goal template id | Goal expansion |
| `next` | workflow node / step | Routing with optional `when` |
| `uses_authority` / `may_use_authority` | `AUTH-*` | Authority scope |

## 11. Fields consumed by runtime components

Planner reads runtime sidecar `navigation` for phase order and gate fields. Graph expansion reads `interactions`, `assumptions`, and workflow edges with `when` conditions. Goal bootstrap uses `goal_expansion` and `expected_parameters`. Flow guidance reads sidecar `texts` and `documentation`. API task creation selects workflow by `id` / `key`.

## 12. Validation procedure

Dedicated validator: `engine/validation/workflow_node_validator.py`.

Audit projection:

```bash
python scripts/audit_current_node_yaml.py --filter workflow
```

Report: `audits/reports/nodes/workflow-node-audit.md`.

Checks:

1. Parse workflow frontmatter (primary YAML).
2. Run `validate_workflow_node(meta)`.
3. Confirm forbidden runtime fields are absent from frontmatter top level (must be under `runtime`).
4. Validate legacy workflow runtime sidecars separately per [workflow-runtime.md](sidecars/workflow-runtime.md) when present.
5. Run `tests/reference/test_workflow_ontology.py` and `tests/mvp/test_desktop_mvp_workflow.py` for integration.

## 13. Common authoring mistakes

- Putting `navigation` or `interactions` in frontmatter instead of `runtime.yaml`.
- Using ids without `WF-` prefix.
- Hardcoding parameter gather lists in Python instead of graph expansion.
- Omitting `metadata.status`.
- Duplicating `title` / `purpose` in frontmatter when they belong in the sidecar.

## 14. Current repository examples

- `workflows/pipe-wall-thickness.yaml`
- `workflows/mawp.yaml`
- `workflows/WF-PIPE-WALL-THICKNESS/runtime.yaml`
- `workflows/WF-MAWP/runtime.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/workflow_node_validator.py` — `validate_workflow_node`, `ALLOWED_WORKFLOW_CLASSES`, `_FORBIDDEN_FIELDS`; audit `--filter workflow` → `audits/reports/nodes/workflow-node-audit.md`
- Tests: `tests/reference/test_workflow_ontology.py`, `tests/reference/test_workflow_audit_process.py`
- Sidecar: `engine/reference/workflow_sidecar.py` — `merge_workflow_sidecar_metadata`, `_RUNTIME_KEYS`, `_PROJECT_RUNTIME_WORKFLOW_IDS`
- Graph build: `engine/graph/graph_builder.py` — workflow sidecar merge at compile
- Legacy aliases: `engine/reference/b313_legacy_aliases.py`
