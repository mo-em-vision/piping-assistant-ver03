# engine/messaging/

Deterministic user-facing prompts for workflow steps and formula parameters (no LLM in this layer).

## Purpose

Format questions, numbered choices, and formula+parameter blocks for CLI chat and API equation display. AI agents call these builders via `ai/response/response_handler.py`.

## Entry Points

| Symbol | File |
|--------|------|
| `build_step_prompt` | `step_prompt.py` |
| `build_formula_parameter_prompt` | `formula_parameter_prompt.py` |
| `format_parameter_block` | `prompt_format.py` |

## Dependencies

**Depends on:** `engine/graph/node_interaction`, `engine/reference/` (reader, formula_display, nomenclature), `engine/planner` (tests), `models/input`

**Used by:** `ai/response/response_handler.py`, `cli/orchestrator.py`, `api/equation_inputs_display.py`

## Runtime Usage

**Active** in chat flow and equation input display API.

## Possible Dead Code

None identified. Large `formula_parameter_prompt.py` is fully exercised by tests and API.

## Notes

- `step_prompt.py` uses lazy import of `GraphEngine` to resolve interaction specs.
- `classify_formula_parameters` used by `api/equation_inputs_display.py` for desktop UI.

## Execution Traces

```
CLI chat (assumption/decision turn)
  → ResponseHandler.format_step_prompt
  → step_prompt.build_step_prompt(reader, task, evaluation)
    → node_interaction specs + prompt_format helpers

Formula parameter collection
  → ResponseHandler.format_formula_parameter_prompt
  → formula_parameter_prompt.build_formula_parameter_prompt
    → formula_display.load_equation_context
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `formula_parameter_prompt.py` | Formula + missing param prompts | `build_formula_parameter_prompt`, `classify_formula_parameters` | response_handler, orchestrator, api |
| `prompt_format.py` | Shared formatting | `format_parameter_block`, `format_numbered_choices` | step_prompt, formula_parameter_prompt, tests |
| `step_prompt.py` | Assumption/decision prompts | `build_step_prompt` | response_handler, tests |
