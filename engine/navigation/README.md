# engine/navigation/

Engine-owned **navigation projection** helpers. These modules derive desktop/API-facing navigation surfaces from the canonical `EngineeringPlan` and graph expansion — they do not replace the Planner or Graph Engine.

## Purpose

| Module | Role |
| --- | --- |
| `missing_inputs.py` | `collect_all_missing` — deduplicated missing field ids from plan + graph state |
| `submittable_projection.py` | `submittable_parameter_ids`, `collection_step_order` — phase-scoped submittable ids and presentation order |
| `composer_mapping.py` | Maps planner parameter ids to composer/timeline step ids |
| `timeline_projection.py` | Graph-driven timeline visibility (`step_applies_for_timeline`, hidden inputs, diameter pair) |
| `timeline_row_ids.py` | User-facing timeline row ids (e.g. `weld_joint_efficiency` vs canonical lookup keys) |
| `timeline_completion.py` | Goal-driven calc/report tail steps from workflow metadata |
| `legacy_timeline_reveal.py` | Timeline reveal for tasks without a stored `EngineeringPlan` |
| `timeline_sync.py` | Persists `timeline_input_order` on task outputs |
| `active_input_projection.py` | Planner-owned composer/timeline reveal when `engineering_plan` is present |

**Removed:** `workflow_path.py` — workflow-specific branching (`is_pipe_wall_*`, `is_mawp_*`) replaced by graph-driven projection above.

## Boundaries

| Layer | Owns |
| --- | --- |
| **Graph Engine** | Active subgraph, `required_user_inputs()`, branch activation |
| **Planner** (`engine/planner/`) | `EngineeringPlan`, phase order, next missing requirements |
| **engine/planning/** | Canonical workflow initiation and execution gating |
| **engine/navigation/** | Read-only projection from plan + facts → API/desktop navigation fields |
| **engine/messaging/** | Deterministic prompt copy |
| **Flow Guidance** (`engine/presentation/`) | Traversal narration and `PresentationResponse` assembly |

Do not treat navigation projection output as navigation authority. Authoritative plan state: `task.outputs["engineering_plan"]`. See [`docs/core/16. task_outputs_authority.md`](../../docs/core/16.%20task_outputs_authority.md).

## Tests

- `tests/engine/navigation/test_navigation_projection_parity.py`
- `tests/navigation/contract/`
