# engine/execution/

Workflow lifecycle event emission during node execution (distinct from `engine/executor/`).

## Purpose

`WorkflowLifecycleEmitter` records which graph nodes activated, completed, or skipped as `_lifecycle_events` on task outputs. `parse_lifecycle_events` reverses storage for UI.

## Entry Points

| Symbol | File |
|--------|------|
| `WorkflowLifecycleEmitter` | `lifecycle_emitter.py` |
| `parse_lifecycle_events`, `is_executable_node` | `lifecycle_emitter.py` |

## Dependencies

**Depends on:** `engine/graph/graph_store`, `engine/graph/node_behaviors`, `engine/graph/doc_templates`, `engine/reference/node_types`, `models/workflow_state`

**Used by:** `engine/executor/executor.py`, `engine/state/workflow_state.py`, `tests/execution/`

## Runtime Usage

**Active** when `StandardsReader.graph_store.available` during `Executor.execute_plan`.

## Possible Dead Code

| Item | Confidence |
|------|------------|
| `execution/__init__.py` | **Low** — docstring only; no exports (intentional) |

## Notes

- Package name collides conceptually with `engine/executor/` — this folder is **telemetry**, not calculation execution.

## Execution Traces

```
Executor.execute_plan (graph store available)
  → WorkflowLifecycleEmitter(store)
  → on each node: emit activated/completed/skipped
  → state.store_output(task_id, "_lifecycle_events", payload)

build_workflow_state
  → parse_lifecycle_events(task.outputs["_lifecycle_events"])
  → presentation blocks.render_lifecycle_context
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Package marker | — | — |
| `lifecycle_emitter.py` | Lifecycle event build/parse | `WorkflowLifecycleEmitter`, `parse_lifecycle_events` | executor, workflow_state |
