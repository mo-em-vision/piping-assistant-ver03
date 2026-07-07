# engine/presentation/

Graph-native UI presentation and Flow Guidance Layer (traversal narration).

## Purpose

Phase 9 presentation layer for the desktop app. Converts workflow parameters, lifecycle events, and graph documentation into canonical block dicts consumed by the API serializers.

The **Flow Guidance Layer** (`docs/rules.md` §21) adds traversal narration — why the workflow is at a step, why a node is active, what happens next. It is presentation-only and separate from deterministic parameter prompts (`engine/messaging/`).

## Entry Points

| Symbol | File |
|--------|------|
| `build_presentation` | `presentation_engine.py` |
| `GuidanceResolver` | `guidance_resolver.py` |
| `ResponseComposer` | `response_composer.py` |
| `guidance_context_from_navigation` | `guidance_resolver.py` |
| `validate_guidance_text` | `guidance_resolver.py` |
| `build_flow_guidance_payload` | `api/flow_guidance.py` (API task-state field) |

## Dependencies

**Depends on:** `engine/presentation/blocks.py`, `engine/presentation/inputs.py`, `engine/graph/documentation_resolver`, `engine/messaging/` (prompt builders), `models/workflow_state`, `models/presentation.py`, `presentation/guidance/workflows/*.yaml`

**Used by:** `engine/state/workflow_state.py`, `api/flow_guidance.py`, `api/chat_orchestrator.py`, `storage/session_store.py`, `tests/presentation/`, `tests/api/`

## Runtime Usage

- `build_presentation` — **active** whenever `build_workflow_state` runs (desktop workflow panel snapshot blocks on `workflow_state.presentation_blocks`).
- `GuidanceResolver` / `ResponseComposer` — **active** on `waiting_input` chat turns (`api/chat_orchestrator.py`) and in every `task_state` payload via `api/flow_guidance.build_flow_guidance_payload()` → `flow_guidance` field (separate from `workflow_state`).
- `storage/session_store.SessionStore.append_message(..., transcript_blocks=...)` — persists append-only turn blocks; `load_cumulative_transcript_blocks()` replays history.

## Flow Guidance vs messaging vs snapshot blocks

| Concern | Owner | Output field |
| --- | --- | --- |
| Traversal narration | `GuidanceResolver` → YAML | `GuidanceBlock` |
| Parameter/step prompts | `engine/messaging/` (`step_prompt.py`, `formula_parameter_prompt.py`, `parameter_input_prompt.py`) | `active_prompt` / prompt blocks |
| Current state snapshot | `ResponseComposer` → `PresentationResponse` | `presentation_blocks` (not stored on workflow state) |
| Graph panel snapshot | `build_presentation` | `workflow_state.presentation_blocks` |
| Append-only history | `ResponseComposer` + session | `transcript_blocks` (display history only) |

Do **not** conflate `presentation_blocks` on `PresentationResponse` with `transcript_blocks` (append-only conversation history). Do **not** attach presentation state to workflow logic.

- Guidance YAML must not duplicate equation bodies or deterministic prompt output from `build_step_prompt()`, `build_formula_parameter_prompt()`, or `build_parameter_input_prompt()`.

## Possible Dead Code

None — `inputs.py` is used internally by `presentation_engine.py` only (not dead).

## Notes

- `blocks.py` optionally calls `display_emitter.emit_equation_blocks` for equation sections.
- Does not perform engineering validation or calculations.
- Desktop UI consumption of `flow_guidance` / `transcript_blocks` is pending; backend payload is exposed on `task_state` and chat responses.

## Execution Traces

```
TaskStateManager → build_workflow_state
  → presentation_engine.build_presentation(workflow_state, reader)
    → inputs.engineering_inputs_from_parameters
    → blocks.render_workflow_documentation
    → blocks.render_parameter_requests / render_lifecycle_context / render_equation_blocks

serializers.task_state
  → api.flow_guidance.build_flow_guidance_payload(task, reader)
    → GuidanceResolver.resolve(GuidanceContext)
      → presentation/guidance/workflows/<workflow_id>.yaml
    → ResponseComposer.compose(...)
      → guidance blocks + engine/messaging prompts → PresentationResponse
    → task_state["flow_guidance"]  (presentation_blocks, transcript_blocks, active_prompt)

api/chat_orchestrator (waiting_input)
  → _compose_flow_guidance(...)
  → ChatResponse.data: presentation + new_transcript_blocks
  → SessionStore.append_message(..., transcript_blocks=new_transcript_blocks)
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Package exports | `build_presentation`, `GuidanceResolver`, `ResponseComposer` | external |
| `blocks.py` | Block builders | `render_*_block`, `render_equation_blocks` | presentation_engine |
| `inputs.py` | WorkflowParameter → EngineeringInput | `engineering_inputs_from_parameters` | presentation_engine |
| `presentation_engine.py` | Snapshot orchestrator | `build_presentation` | workflow_state |
| `guidance_resolver.py` | Traversal narration resolver | `GuidanceResolver`, `guidance_context_from_navigation`, `validate_guidance_text` | flow_guidance, chat_orchestrator, tests |
| `response_composer.py` | Merge guidance + prompts | `ResponseComposer`, `append_transcript_blocks` | flow_guidance, chat_orchestrator, session_store, tests |
