# engine/state/

In-memory engineering task lifecycle and adapters to `WorkflowState` / presentation.

## Purpose

`TaskStateManager` holds session tasks (inputs, outputs, status) with **no workflow logic**. `workflow_state.py` projects task + graph into `models.workflow_state.WorkflowState` for the desktop API.

## Entry Points

| Symbol | File |
|--------|------|
| `TaskStateManager` | `state_manager.py` |
| `build_workflow_state` | `workflow_state.py` |
| `build_node_outputs` | `node_outputs.py` |

## Dependencies

**Depends on:** `engine/reference/`, `engine/graph/`, `engine/presentation/`, `engine/execution/`, `models/task`, `models/workflow_state`

**Used by:** `api/`, `cli/`, `storage/project_session_store.py`, `engine/executor/`, `engine/planner/`, `engine/inspection/`

## Runtime Usage

**Active.** One `TaskStateManager` per API session / CLI session / test fixture.

## Possible Dead Code

| Item | Confidence |
|------|------------|
| `workflow_parameters._param_nodes_by_input_id`, `_resolve_active_nodes` | **Low** — private; used by `api/node_provenance.py` |

## Notes

- Persistence to SQLite is in `storage/`, not here — this layer is session RAM.
- `build_workflow_state` is the bridge between backend task model and desktop `workflow_state` JSON.

## Execution Traces

```
api/desktop_service / cli/session_store
  → TaskStateManager.create_task / store_input / store_output
  → state_manager.build_workflow_state (on read)
    → workflow_state.build_workflow_state
      → workflow_parameters, node_outputs, presentation_engine
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Public exports | `TaskStateManager`, `build_workflow_state` | widespread |
| `node_outputs.py` | Per-node output slices for UI | `build_node_outputs` | workflow_state, tests |
| `state_manager.py` | **Task CRUD** | `TaskStateManager`, errors | api, cli, storage, executor |
| `workflow_parameters.py` | Graph-backed parameter map | helpers for active nodes | workflow_state, node_provenance |
| `workflow_state.py` | Task → WorkflowState | `build_workflow_state` | state_manager, inspection, tests |

### state_manager.py — detail

- **Inputs:** task_id, `EngineeringInput`, output keys, step progress
- **Outputs:** `Task`, `WorkflowState` (via adapter)
- **Side effects:** In-memory dict mutation only

### workflow_state.py — detail

- **Inputs:** `Task`, `StandardsReader`, step progress
- **Outputs:** `WorkflowState` with parameters, blocks, lifecycle
- **Imports:** `presentation_engine.build_presentation`, `parse_lifecycle_events`
