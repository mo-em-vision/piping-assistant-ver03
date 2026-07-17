# engine/navigation/

Engine-owned **navigation projection** helpers. These modules derive desktop/API-facing navigation surfaces from the canonical `EngineeringPlan` and graph expansion — they do not replace the Planner or Graph Engine.

## Purpose

| Module | Role |
| --- | --- |
| `missing_inputs.py` | `collect_all_missing` — deduplicated missing field ids from plan + graph state |
| `submittable_projection.py` | `submittable_parameter_ids`, `collection_step_order` — which parameters are submittable in phase order |
| `composer_mapping.py` | Maps planner parameter ids to composer/timeline step ids |
| `workflow_path.py` | Workflow-specific timeline helpers (hidden inputs, step applicability) |

## Boundaries

| Layer | Owns |
| --- | --- |
| **Graph Engine** | Active subgraph, `required_user_inputs()`, branch activation |
| **Planner** (`engine/planner/`) | `EngineeringPlan`, phase order, next missing requirements |
| **engine/navigation/** | Read-only projection from plan + facts → API/desktop navigation fields |
| **engine/messaging/** | Deterministic prompt copy |
| **Flow Guidance** (`engine/presentation/`) | Traversal narration and `PresentationResponse` assembly |

Do not treat navigation projection output as navigation authority. Authoritative plan state: `task.outputs["engineering_plan"]`. See [`docs/core/16. task_outputs_authority.md`](../../docs/core/16.%20task_outputs_authority.md).

## Tests

- `tests/engine/navigation/test_navigation_projection_parity.py`
