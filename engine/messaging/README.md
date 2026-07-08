# engine/messaging/

Deterministic user-facing prompts for workflow steps and formula parameters (no LLM in this layer).

## Purpose

Format questions, numbered choices, and formula+parameter blocks for CLI chat, API task state, and desktop workflow composer. **Owns deterministic user-facing prompt copy** for workflow parameter asks (planner owns navigation only — see `docs/rules.md` §12).

## Entry Points

| Symbol | File |
|--------|------|
| `build_parameter_input_prompt` | `parameter_input_prompt.py` |
| `parameter_metadata_context` | `parameter_prompt_context.py` |
| `default_workflow_parameter_prompt` | `workflow_parameter_prompts.py` |
| `build_interaction_step_prompt` | `step_prompt.py` |
| `build_formula_parameter_prompt` | `formula_parameter_prompt.py` |
| `render_parameter_prompt` | `prompt_format.py` |

## Resolution order

All desktop/API parameter asks resolve through `build_parameter_input_prompt()` in this order:

1. Workflow interaction spec / `runtime.yaml` (gate phases use numbered formatting from `step_prompt.py`)
2. PARAM-* node `question`, then `description` (via `parameter_prompt_context.py`)
3. Equation or lookup context (`formula_parameter_prompt.py`)
4. Legacy `phase_questions` (backward compatibility)
5. Default catalog (`workflow_parameter_prompts.py`)
6. Final messaging fallback (`parameter_display_label()` + phase context)

PARAM metadata is read through existing reference/graph accessors in `parameter_prompt_context.py`. The Graph Engine does not own user-facing wording.

## Desktop vs CLI paths

| Consumer | Primary prompt source | Notes |
|----------|----------------------|-------|
| Desktop workflow composer | `current_ask.prompt`, `parameter.guidance` | Both call `build_parameter_input_prompt()` |
| CLI / transcript | `flow_guidance.active_prompt` | May use full formula blocks via `ResponseComposer` |

Active input asks must not fall back to the frontend generic string when a `parameter_id` is known.

## Dependencies

**Depends on:** `engine/graph/node_interaction`, `engine/reference/` (reader, formula_display, nomenclature), `models/input`

**Used by:** `ai/response/response_handler.py`, `api/chat_orchestrator.py`, `api/parameter_definitions.py`, `engine/planner/goal_navigation.py`

## Runtime Usage

**Active** in chat flow, task state serialization, and equation input display API.

## Execution Traces

```
Desktop composer (per-parameter ask)
  → build_current_ask / _parameter_guidance
  → build_parameter_input_prompt(reader, task, parameter_id)
    → step_prompt.build_interaction_step_prompt (gate phases)
    → parameter_prompt_context.parameter_metadata_context
    → formula_parameter_prompt.guidance_for_parameter_input
    → workflow_parameter_prompts.default_workflow_parameter_prompt

CLI chat (assumption/decision turn)
  → ResponseHandler.format_step_prompt
  → step_prompt.build_step_prompt(reader, task, navigation_plan)
    → node_interaction specs + prompt_format helpers

Formula parameter collection (CLI / flow_guidance)
  → ResponseHandler.format_formula_parameter_prompt
  → formula_parameter_prompt.build_formula_parameter_prompt
    → formula_display.load_equation_context
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `parameter_input_prompt.py` | Single entry point for per-parameter asks | `build_parameter_input_prompt` | goal_navigation, parameter_definitions, planner |
| `parameter_prompt_context.py` | PARAM metadata read (messaging-owned) | `parameter_metadata_context`, `parameter_prompt_from_metadata` | parameter_input_prompt |
| `formula_parameter_prompt.py` | Formula + missing param prompts | `build_formula_parameter_prompt`, `guidance_for_parameter_input` | response_handler, orchestrator, api |
| `prompt_format.py` | Shared formatting + assembly | `format_parameter_block`, `render_parameter_prompt` | step_prompt, formula_parameter_prompt, parameter_input_prompt |
| `step_prompt.py` | Assumption/decision numbered prompts | `build_step_prompt`, `build_interaction_step_prompt` | response_handler, parameter_input_prompt |
| `workflow_parameter_prompts.py` | Fallback prompt catalog | `default_workflow_parameter_prompt` | parameter_input_prompt |
