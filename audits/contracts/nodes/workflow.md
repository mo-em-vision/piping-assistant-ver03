# Workflow Node Contract

## 1. Purpose

A workflow node defines a reusable engineering objective — what kind of task it is, which authorities and parameters may participate, and how goals expand — without executing calculations or storing runtime state.

## 2. Use this node when

- You are defining an end-to-end engineering task (pipe wall thickness design, MAWP).
- You need goal templates, entry paragraphs, and expected parameter sets.
- Navigation phase order and gate fields belong in the nested `runtime` block on the primary workflow YAML.

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
| `entry_points` | Definition anchor (`role: definition_anchor`) aligned with root goal target parameter |
| `expected_parameters` | Bootstrap hint only — anticipated `PARAM-*` for goal planning. **Active parameter asks** are authoritative from graph expansion `required_user_inputs()` per `docs/rules.md` §13. |
| `goal_expansion` | Root and child goal templates, including `root_goal.completion` |
| `applicability.applies_to` | `CONCEPT-*` filters |
| `report` | Report section requirements |
| `runtime.navigation` | **Canonical** phase order and gate fields — see [Navigation phases](#navigation-phases-canonical-authoring) |
| `edges` | `may_use_equation`, `may_use_lookup`, `next`, etc. — **not** `starts_from_*` on workflows |

### Navigation phases (canonical authoring)

Phase order is authored **only** inside the nested `runtime.navigation` block on the primary workflow YAML:

```yaml
runtime:
  navigation:
    assumption_gate_fields:
      - straight_pipe_section
    phases:
      expansion_assumptions: []
      path_decisions: []
      parameter_gathering: []
      coefficient_resolution: []
      execution_assumptions: []
      definition_equation_completion: []
```

| Rule | Detail |
| --- | --- |
| **Canonical location** | `runtime.navigation.phases` — a map from phase key to ordered **task-input field keys** (snake_case). |
| **Runtime consumer** | `extract_nested_blocks` promotes `runtime` → flattened `navigation`; `load_workflow_navigation()` reads `navigation.phases` (`engine/graph/workflow_navigation.py`). |
| **Single surface** | Author phases on this surface only. Do **not** duplicate phase lists at frontmatter top level or in separate navigation sidecars when `runtime.navigation` is present. |
| **Legacy synthesis** | Top-level `phases: [{key, required_parameters}]` is converted to `navigation` **only when** `runtime.navigation` is absent (`merge_workflow_sidecar_metadata` / `_phases_to_navigation`). Do not author both. |
| **Ordering only** | Phases order planner navigation among fields graph expansion has already made active. They do **not** add parameters to the expanded graph or override `required_user_inputs()`. |
| **Resolvable references** | Every listed field key must correspond to an existing canonical `PARAM-*` node (or an explicitly authored assumption/decision field permitted by graph expansion). |
| **Lookup inputs vs outputs** | List **lookup binding keys** users supply (e.g. `material_grade`, `pipe_construction_type`, `nominal_pipe_size`). Do **not** list lookup **outputs** (e.g. `allowable_stress`, `basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes`, `weld_strength_reduction_factor_w`, `temperature_coefficient_y`, `actual_wall_thickness` when resolved by lookup). |
| **Equation outputs** | Do **not** list equation-calculated or goal-target parameters in interactive phases. |

**Legacy top-level `phases` (do not author with `runtime.navigation`):**

```yaml
# synthesized only when runtime.navigation is absent — not canonical
phases:
  - key: parameter_gathering
    required_parameters:
      - PARAM-material-grade
```


### Allowed `workflow_class` values

```text
design_calculation, verification, inspection, assessment, lookup,
selection, reporting, screening, troubleshooting
```

## 9. Forbidden fields

Forbidden in **frontmatter** top level (must be nested under `runtime:`):

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
| `may_use_equation` | equation id | Participating equations |
| `may_use_lookup` | lookup id | Participating lookups |
| `may_use_validation_rule` | validation rule id | Participating checks |
| `requires_parameter` | `PARAM-*` | Expected inputs |
| `may_create_goal` | goal template id | Goal expansion |
| `next` | workflow node / step | Routing with optional `when` |
| `uses_authority` / `may_use_authority` | `AUTH-*` | Authority scope |

### Goal anchor and completion (calculation workflows)

For **design_calculation** workflows (and similar calculation workflows):

1. **Must** set `goal_expansion.root_goal.target_parameter` to the calculated `PARAM-*` output.
2. **Must** set exactly one `entry_points` item with `role: definition_anchor` whose `parameter` equals that same `PARAM-*` id.
3. **Must** declare completion on the root goal:

```yaml
goal_expansion:
  root_goal:
    goal_class: calculation_goal
    target_parameter: PARAM-...
    completion:
      when: target_parameter_satisfied
      status: finished
```

4. **Do not** author `starts_from_parameter` or `starts_from_paragraph` edges on workflow nodes — `validate_workflow_node` rejects them. Use `entry_points` with `role: definition_anchor` instead.

Runtime anchor resolution (`workflow_anchor_target`) reads the `definition_anchor` entry point first. Completion means the workflow is **finished** when the root target parameter has an expansion-ready fact (same condition used for root goal `SATISFIED`).

### `starts_from_*` edge direction (taxonomy)

Relationship taxonomy (`engine/reference/relationship_taxonomy.py`) defines these edges **workflow-sourced only**. Author them on the workflow node's `edges` list when legacy graphs require them — never on paragraph, equation, or other node types:

| Edge type | Source node | Target |
| --- | --- | --- |
| `starts_from_paragraph` | `workflow` | paragraph id (e.g. `304.1.2-a`) |
| `starts_from_parameter` | `workflow` | `PARAM-*` |

There is no `starts_from_equation` edge type. Equation participation uses `may_use_equation` (or graph expansion from paragraph/equation `authority` links), not `starts_from_*`.

Do **not** place `starts_from_paragraph` or `starts_from_parameter` on paragraph or equation nodes. For new calculation workflows, prefer `entry_points` / `definition_anchor` over new `starts_from_*` workflow edges.

## 11. Fields consumed by runtime components

Planner reads nested `runtime.navigation` for phase order and gate fields only (does not determine active paths). Graph expansion reads graph node `assumptions`, `applicability`, workflow `runtime.interactions`, and workflow edges with `when` conditions to determine active paths and parameter asks. Goal bootstrap uses `goal_expansion` and `expected_parameters` (planning hints only — graph expansion is authoritative for which parameters are actually asked). Flow guidance reads nested `runtime.texts` and `runtime.documentation`. API task creation selects workflow by `id` / `key`.

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
4. Confirm runtime-only fields are nested under `runtime` in the primary workflow YAML (legacy separate runtime file sidecars are obsolete — do not author).
5. Run `tests/reference/test_workflow_ontology.py` and `tests/mvp/test_desktop_mvp_workflow.py` for integration.

## 13. Common authoring mistakes

- Putting `navigation` or `interactions` at frontmatter top level instead of under nested `runtime:`.
- Using ids without `WF-` prefix.
- Hardcoding parameter gather lists in Python instead of graph expansion.
- Omitting `metadata.status`.
- Duplicating `title` / `purpose` in frontmatter when they belong under nested `runtime:`.
- Authoring `starts_from_parameter` or `starts_from_paragraph` on paragraph or equation nodes (workflow is the only permitted source type in the taxonomy).
- Authoring `starts_from_parameter` or `starts_from_paragraph` on workflow nodes instead of aligning `entry_points` with `goal_expansion.root_goal.target_parameter`.
- Omitting `goal_expansion.root_goal.completion` or mismatching `entry_points.definition_anchor.parameter` with `target_parameter`.
- Duplicating phase declarations at frontmatter top level (`phases:`) and under `runtime.navigation.phases`.
- Listing lookup-derived outputs or equation outputs in `runtime.navigation.phases` (users supply lookup **keys** only).

## 14. Current repository examples

- `workflows/pipe-wall-thickness.yaml`
- `workflows/mawp.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/workflow_node_validator.py` — `validate_workflow_node`, `ALLOWED_WORKFLOW_CLASSES`, `_FORBIDDEN_FIELDS`; audit `--filter workflow` → `audits/reports/nodes/workflow-node-audit.md`
- Tests: `tests/reference/test_workflow_ontology.py`, `tests/reference/test_workflow_audit_process.py`, `tests/graph/test_workflow_goal_completion.py` (rejects `starts_from_*` on workflow nodes), `tests/reference/test_relationship_taxonomy.py` (workflow-only source types)
- Runtime merge: `engine/reference/workflow_sidecar.py` — `merge_workflow_sidecar_metadata`, `_RUNTIME_KEYS` (reads nested `runtime` from primary YAML; legacy file sidecar loading disabled)
- Graph build: `engine/graph/graph_builder.py` — workflow runtime metadata merge at compile
- Legacy aliases: `engine/reference/b313_legacy_aliases.py`
