# engine/presentation/

Graph-native UI presentation: build display blocks from `WorkflowState` and the knowledge graph.

## Purpose

Phase 9 presentation layer for the desktop app. Converts workflow parameters, lifecycle events, and graph documentation into canonical block dicts consumed by the API serializers.

## Entry Points

| Symbol | File |
|--------|------|
| `build_presentation` | `presentation_engine.py` |

## Dependencies

**Depends on:** `engine/presentation/blocks.py`, `engine/presentation/inputs.py`, `engine/graph/documentation_resolver`, `models/workflow_state`

**Used by:** `engine/state/workflow_state.py`, `tests/presentation/`

## Runtime Usage

**Active** whenever `build_workflow_state` runs (desktop workflow panel).

## Possible Dead Code

None — `inputs.py` is used internally by `presentation_engine.py` only (not dead).

## Notes

- `blocks.py` optionally calls `display_emitter.emit_equation_blocks` for equation sections.
- Does not perform engineering validation or calculations.

## Execution Traces

```
TaskStateManager → build_workflow_state
  → presentation_engine.build_presentation(workflow_state, reader)
    → inputs.engineering_inputs_from_parameters
    → blocks.render_workflow_documentation
    → blocks.render_parameter_requests / render_lifecycle_context / render_equation_blocks
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Export `build_presentation` | — | external |
| `blocks.py` | Block builders | `render_*_block`, `render_equation_blocks` | presentation_engine |
| `inputs.py` | WorkflowParameter → EngineeringInput | `engineering_inputs_from_parameters` | presentation_engine |
| `presentation_engine.py` | **Orchestrator** | `build_presentation` | workflow_state |
