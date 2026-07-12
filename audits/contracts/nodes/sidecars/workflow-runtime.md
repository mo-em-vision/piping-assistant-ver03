# Workflow Runtime Sidecar Contract

## 1. Purpose

The workflow runtime sidecar (`runtime.yaml`) holds navigation phase order, gate fields, interactions, embedded texts, and workflow-local documentation — separated from the slim workflow frontmatter node.

## 2. Use this sidecar when

- You need `navigation.phases` and `assumption_gate_fields` for a `WF-*` workflow.
- Workflow-specific `interactions`, `texts`, or `documentation` exceed frontmatter scope.
- You are configuring `goal_output`, `engineering_intent`, or `suggested_workflows`.

## 3. Do not use this sidecar when

- You are defining the workflow identity, class, or description (workflow frontmatter).
- You need standards paragraph text or equations (separate node files).
- You need global parameter definitions (`PARAM-*` nodes).

## 4. File location

`workflows/{WF-ID}/runtime.yaml`

Example: `workflows/WF-PIPE-WALL-THICKNESS/runtime.yaml` pairs with `workflows/pipe-wall-thickness.yaml`.

## 5. ID convention

No node `id` in the sidecar. Parent workflow frontmatter carries `id: WF-*`. Sidecar `slug` and `engineering_intent` should match the workflow `key` when present.

## 6. Copyable minimal YAML skeleton

```yaml
navigation:
  assumption_gate_fields:
    - straight_pipe_section
    - pressure_loading
  phases:
    expansion_assumptions:
      - straight_pipe_section
    path_decisions:
      - pressure_loading
    parameter_gathering:
      - internal_design_gage_pressure
interactions:
  - variable: pressure_loading
    mode: decision
    required: true
    required_for_expansion: true
    options:
      - internal_pressure
      - external_pressure
slug: pipe_wall_thickness_design
engineering_intent: pipe_wall_thickness_design
```

## 7. Required fields

No single key is mandatory for an empty runtime file. Valid keys:

```text
navigation, assumptions, interactions, provisional_assumptions, inputs,
equations, conditions, nomenclature, texts, documentation,
suggested_workflows, goal_output, engineering_intent, slug, title,
purpose, status, version
```

Active workflows should include `navigation` with `phases` when not synthesized from frontmatter `phases`.

## 8. Optional fields

| Key | Purpose |
| --- | --- |
| `navigation.assumption_gate_fields` | Pre-expansion gate parameter keys |
| `navigation.phases.*` | Phase-ordered field lists (machine keys) |
| `interactions` | Decision gates and options |
| `assumptions` | Workflow-level assumptions |
| `provisional_assumptions` | Defaults pending confirmation |
| `texts` | Embedded `type: text` blocks |
| `documentation` | Summary and report copy |
| `suggested_workflows` | Related workflow keys |
| `goal_output` | Primary output parameter key |
| `engineering_intent` | Machine intent identifier |
| `slug` | Routing slug |
| `title`, `purpose` | Display metadata |
| `status`, `version` | Lifecycle (overrides when merged) |

Field names under `navigation.phases` use machine keys (snake_case), mapped from `PARAM-*` ids at load time.

## 9. Forbidden fields

```text
id, type, workflow_class, key, edges, links
```

Do not duplicate workflow frontmatter identity fields. Never put `navigation` in workflow frontmatter — validator forbids it.

## 10. Permitted outgoing relationships

Runtime sidecars do not use graph `edges`. Reference parameters by machine field keys in `navigation` and `interactions`. Embedded `texts` may include `id` for text node compilation.

## 11. Fields consumed by runtime components

Workflow sidecar merge injects runtime keys before graph build. Planner reads merged `navigation` for phase order and missing field detection. Expansion policy evaluates `interactions` and gate fields. Flow guidance reads `texts` and `documentation`. API bootstrap maps `PARAM-*` ids to navigation field names via loader mapping tables.

## 12. Validation procedure

1. Confirm parent workflow frontmatter passes `validate_workflow_node` (no forbidden runtime fields).
2. Confirm `runtime.yaml` lives under `workflows/{WF-ID}/`.
3. Confirm phase field keys correspond to known `PARAM-*` nodes.
4. Run MVP workflow test: `python -m pytest tests/mvp/test_desktop_mvp_workflow.py`.
5. Run desktop verify when changing navigation: `cd desktopApp && npm run verify:mvp`.

## 13. Common authoring mistakes

- Putting `navigation` in workflow frontmatter instead of runtime sidecar.
- Using `PARAM-*` ids in `navigation.phases` instead of machine field keys.
- Omitting `assumption_gate_fields` for interactions marked `required_for_expansion`.
- Duplicating `title`/`purpose` in both frontmatter and sidecar inconsistently.
- Hardcoding phase lists in Python instead of maintaining runtime.yaml.

## 14. Current repository examples

- `workflows/WF-PIPE-WALL-THICKNESS/runtime.yaml`
- `workflows/WF-MAWP/runtime.yaml`

## 15. Implementation evidence appendix

- Loader keys: `engine/reference/workflow_sidecar.py` — `_RUNTIME_KEYS`, `merge_workflow_sidecar_metadata`, `_PARAM_TO_FIELD`, `_PROJECT_RUNTIME_WORKFLOW_IDS`
- Runtime path resolution: `engine/reference/workflow_sidecar.py` — `_project_runtime_paths`
- Frontmatter forbidden: `engine/validation/workflow_node_validator.py` — `_FORBIDDEN_FIELDS`
- Graph merge: `engine/graph/graph_builder.py`
