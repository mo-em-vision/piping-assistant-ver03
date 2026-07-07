# ai/ — Architecture Audit

Audited: 2026-07-01. Static analysis only; no code changes.

## Purpose

`ai/` is the **navigation and communication intelligence layer**. It wraps OpenAI chat completions for structured JSON agent outputs, loads markdown prompt templates, parses user chat into `EngineeringInput` values, and formats agent results into user-facing text.

It does **not** own engineering calculations, graph traversal, or standards logic. Those live in `engine/`. Agents propose paths, request inputs, explain selections, and polish report wording — deterministic backends remain authoritative.

## Files

### Package root

| File | Role |
| --- | --- |
| `__init__.py` | Re-exports six core agents, `OpenAIClient`, `MissingAPIKeyError`, `ResponseHandler` |
| `client.py` | OpenAI JSON-completion wrapper (`LLMClient` protocol, `OpenAIClient`) |
| `prompts_loader.py` | Cached loader for `ai/prompts/*.md` |
| `interaction_specs.py` | Cached decision-interaction specs from standards node `B313-304.1.1` |
| `input_extractor.py` | Regex/heuristic pipe wall thickness input extraction from chat |
| `user_response_extractor.py` | Generic pending-interaction response parsing (confirm/override/decision) |

### `agents/`

Specialized agent classes. See [agents/README.md](agents/README.md) for per-agent inventory.

### `prompts/`

Markdown system prompts for LLM agents. Loaded via `prompts_loader.load_prompt()` or `BaseAgent.prompt_file`.

| File | Loaded at runtime? |
| --- | --- |
| `intent_agent.md` | Yes — `IntentAgent` |
| `planner_agent.md` | Yes — `PlannerAgent` (LLM fallback only) |
| `input_agent.md` | Yes — `InputAgent` (optional LLM enrichment) |
| `routing_agent.md` | Yes — `RoutingAgent` (LLM fallback) |
| `intent_detection.md` | Yes — `ContextAgent` |
| `engineering_report_enhancement.md` | Yes — `SynthesisAgent` |
| `report_explanation.md` | Yes — `SynthesisAgent.explain_section` |
| `task_assist.md` | Yes — `TaskAssistAgent` |
| `task_continuation.md` | Yes — `TaskContinuationAgent` |
| `selection_explanation.md` | Yes — `SelectionExplainAgent` |
| `node_selection.md` | **No** — documented only in `docs/core/` |
| `missing_information.md` | **No** — documented only in `docs/core/` |
| `synthesis_agent.md` | **No** — no code references |
| `planner/intent_detection.md` | **No** — referenced in `planner_agent.md` text only |
| `planner/node_selection.md` | **No** — referenced in `planner_agent.md` text only |
| `planner/question_generation.md` | **No** — referenced in `planner_agent.md` text only |
| `planner/ambiguity_resolution.md` | **No** — referenced in `planner_agent.md` text only |

### `response/`

| File | Role |
| --- | --- |
| `__init__.py` | Re-exports `ResponseHandler` |
| `response_handler.py` | Formats `models.agent` results and delegates to `engine.messaging` prompts |

## Entry Points

| Entry | Runnable? | Notes |
| --- | --- | --- |
| `ai/__init__.py` | No | Package import surface |
| `OpenAIClient.from_settings()` | Indirect | Called when agents need an LLM and no client is injected |
| `extract_pipe_wall_thickness_inputs()` | Indirect | Called from `api/chat_orchestrator.py` on every active-task chat message |
| Agent `.analyze()` / `.plan()` / `.reply()` / etc. | Indirect | Invoked by `api/chat_orchestrator.py`, `api/chat_service.py`, `api/task_continuation_service.py`, `engine/reports/presentation.py` |
| `prompts_loader.load_prompt()` | Indirect | Called from `BaseAgent` and a few agents with `extra_system` |

Nothing in `ai/` has `if __name__ == "__main__"`.

## Dependencies

### Internal

```
ai/__init__.py          → agents/, client.py, response/
ai/agents/base.py       → client.py, prompts_loader.py
ai/agents/*.py          → base.py, _constants.py, source_utils.py (some)
ai/input_extractor.py   → interaction_specs.py, user_response_extractor.py
ai/interaction_specs.py → engine/graph/node_interaction.py, engine/reference/standards_reader.py
ai/response/            → input_extractor.py (InputRejection), models/agent.py
```

### External (folders/files this package imports)

| Source | Used by |
| --- | --- |
| `config/settings.py` | `client.py` (`Settings`, `settings`) |
| `openai` (third-party) | `client.py` (lazy import in `OpenAIClient.__init__`) |
| `engine/router.py` | `intent_agent.py`, `routing_agent.py` |
| `engine/planner/planner.py` | `planner_agent.py` |
| `engine/state/state_manager.py` | `planner_agent.py`, `input_agent.py` |
| `engine/reference/standards_reader.py` | `planner_agent.py`, `interaction_specs.py`; TYPE_CHECKING in `response_handler.py` |
| `engine/executor/unit_manager.py` | `input_extractor.py` |
| `engine/reference/material_ids.py` | `input_extractor.py` |
| `engine/graph/node_interaction.py` | `user_response_extractor.py`, `interaction_specs.py` |
| `engine/messaging/formula_parameter_prompt.py` | `response_handler.py` (lazy) |
| `engine/messaging/step_prompt.py` | `response_handler.py` (lazy) |
| `engine/reports/formatters.py` | `synthesis_agent.py` (lazy) |
| `models/agent.py` | All agents, `response_handler.py` |
| `models/input.py` | `input_extractor.py`, `user_response_extractor.py` |
| `models/planning.py` | `planner_agent.py`, `input_agent.py`, `response_handler.py` |
| `models/task.py` | `planner_agent.py`, `input_agent.py`, `response_handler.py` |
| `models/report.py` | `synthesis_agent.py` |

`ai/` does **not** import from `api/`, `desktopApp/`, or `storage/`.

### Dependents (grep: `from ai.` / `import ai.`)

| Area | Imports |
| --- | --- |
| `api/chat_orchestrator.py` | `ContextAgent`, `InputAgent`, `IntentAgent`, `PlannerAgent`, `missing_pipe_inputs`, `OpenAIClient`, `MissingAPIKeyError`, `extract_pipe_wall_thickness_inputs`, `default_pipe_wall_thickness_decision_interactions`, `ResponseHandler` |
| `api/chat_service.py` | `SelectionExplainAgent`, `TaskAssistAgent` (orchestrator also used) |
| `api/task_continuation_service.py` | `TaskContinuationAgent` |
| `api/parameter_definitions.py` | `default_pipe_wall_thickness_decision_interactions` |
| `engine/reports/presentation.py` | `SynthesisAgent` |
| `tests/agents/`, `tests/ai/`, `tests/graph/`, `tests/acceptance/`, `tests/mvp/` | Various agents and extractors |

No `from ai import …` usage found; consumers import submodule paths.

## Runtime Usage

**Yes — on multiple execution paths.**

Evidence:

1. **CLI / desktop chat workflow** (`api/chat_orchestrator.py`): `IntentAgent` → `PlannerAgent` → `InputAgent` + `ContextAgent`; `extract_pipe_wall_thickness_inputs` stores inputs; `ResponseHandler` formats prompts. Used by `api/chat_service.py` via `ChatOrchestrator`.
2. **Desktop chat Q&A** (`api/chat_service.py`): `TaskAssistAgent`, `SelectionExplainAgent` for follow-up questions and highlight explanations.
3. **Task continuation** (`api/task_continuation_service.py`): `TaskContinuationAgent.suggest()` after task completion.
4. **Report presentation** (`engine/reports/presentation.py` ← `report_generator.py`): optional `SynthesisAgent` narrative enhancement when `use_ai=True`.
5. **Parameter definitions API** (`api/parameter_definitions.py`): decision interaction specs for pipe wall thickness.

`RoutingAgent` is implemented and tested but **not** wired into `api/chat_orchestrator.py` or `api/` (see Possible Dead Code).

## Possible Dead Code

| Symbol / file | Why it appears unused | Confidence |
| --- | --- | --- |
| `ai/agents/routing_agent.py` (`RoutingAgent`) | Only imported in `ai/__init__.py`, `ai/agents/__init__.py`, and `tests/agents/test_routing_context_agents.py`. Not used by orchestrator or API. | **High** |
| `ai/prompts/node_selection.md`, `missing_information.md`, `synthesis_agent.md` | Never passed to `load_prompt()`. Referenced in design docs only. | **High** |
| `ai/prompts/planner/*.md` (4 files) | Listed as "reference only" inside `planner_agent.md`; never loaded programmatically. | **High** |
| `user_response_extractor.extract_explicit_interaction_value` | Defined; grep finds **no callers** outside its module. | **High** |
| `prompts_loader.prompts_dir()` | Defined; **no callers** outside `prompts_loader.py`. | **High** |
| `SynthesisAgent._fallback_presentation` | Static method defined; **never called** (enhancement falls back to `base_markdown`). | **High** |
| `ai/__init__.py` re-exports | No `from ai import` consumers found. | **Medium** |

Do not delete based on this audit alone.

## Notes

### Duplicate / parallel implementations

1. **Intent classification**: `engine.router.route()` (deterministic, primary in `IntentAgent`) vs `IntentAgent._analyze_with_llm()` vs unused `RoutingAgent`.
2. **Planning**: `engine.planner.Planner` (primary in `PlannerAgent.plan_navigation`) vs `PlannerAgent._plan_with_llm()` fallback when `action == CLARIFY`.
3. **Input identification**: `InputAgent._missing_inputs()` from `NavigationPlan` / static field lists vs optional `InputAgent._enrich_with_llm()`.
4. **Input extraction**: `input_extractor.extract_pipe_wall_thickness_inputs()` (deterministic regex) runs in orchestrator **before** agents; separate from `InputAgent` missing-input analysis.
5. **Intent-detection prompts**: `intent_agent.md`, `intent_detection.md`, and `planner/intent_detection.md` — three similarly named prompt files; only the first two are loaded (by different agents).
6. **ContextAgent double-load**: `prompt_file = "intent_detection.md"` and `_evaluate_with_llm` passes `extra_system=load_prompt("intent_detection.md")` again — same content appended twice when LLM path runs.
7. **SynthesisAgent double-load**: `prompt_file` and `enhance_engineering_report` both reference `engineering_report_enhancement.md` via `extra_system`.

### Boundary rule

Agents and synthesis must not alter engineering numeric values. `SynthesisAgent._assert_values_preserved` enforces this for enhanced reports.

---

## Execution traces

### Trace A — New chat message (active task, desktop / CLI)

```
User message (desktop chat or CLI)
    ↓
api/chat_service.py → ChatOrchestrator.handle_message()   [api/chat_orchestrator.py]
    ↓
extract_pipe_wall_thickness_inputs()   [ai/input_extractor.py]
    → user_response_extractor (pending decisions / confirmations)
    → TaskStateManager.store_input()
    ↓
ContextAgent.evaluate()   [ai/agents/context_agent.py]
    → (if context_switch) early return
    ↓
IntentAgent.analyze()   [ai/agents/intent_agent.py]
    → engine.router.route() OR LLM (intent_agent.md)
    ↓
PlannerAgent.plan_navigation()   [ai/agents/planner_agent.py]
    → engine.planner.Planner.plan()
    → optional LLM fallback (planner_agent.md)
    ↓
InputAgent.analyze()   [ai/agents/input_agent.py]
    → optional LLM enrichment (input_agent.md)
    ↓
ResponseHandler.format_step_prompt() | format_formula_parameter_prompt() | format_input_requests()
    [ai/response/response_handler.py]
    → engine.messaging.step_prompt | formula_parameter_prompt
    ↓
CLIResponse → api/chat_service → desktop UI
```

### Trace B — Task assist (chat tab Q&A)

```
User follow-up question
    ↓
api/chat_service.py (task assist endpoint)
    → build_task_context_brief(), retrieve_standards_context()
    ↓
TaskAssistAgent.reply()   [ai/agents/task_assist_agent.py]
    → OpenAIClient.complete_json_messages() + task_assist.md
    → normalize_chat_sources()   [ai/agents/source_utils.py]
    ↓
Serialized chat message → desktop UI
```

### Trace C — Selection explain (highlighted text)

```
User highlights workspace text
    ↓
api/chat_service.py (selection explain endpoint)
    ↓
SelectionExplainAgent.explain()   [ai/agents/selection_explain_agent.py]
    → selection_explanation.md
    ↓
Serialized explanation → desktop UI
```

### Trace D — Continuation suggestions (completed task)

```
GET continuation suggestions
    ↓
api/task_continuation_service.py
    ↓
TaskContinuationAgent.suggest()   [ai/agents/task_continuation_agent.py]
    → task_continuation.md OR fallback_suggestions()
    ↓
JSON suggestions → desktop UI
```

### Trace E — AI report presentation (optional)

```
Report generation (use_ai=True)
    ↓
engine/reports/report_generator.py
    ↓
engine/reports/presentation.py
    → SynthesisAgent.enhance_engineering_report() / explain_section()
    → engineering_report_enhancement.md, report_explanation.md
    ↓
Enhanced markdown in report payload
```

---

## Per-file inventory

### `__init__.py`

| | |
| --- | --- |
| **Purpose** | Public package surface for core navigation agents and client |
| **Public** | `ContextAgent`, `InputAgent`, `IntentAgent`, `PlannerAgent`, `RoutingAgent`, `SynthesisAgent`, `MissingAPIKeyError`, `OpenAIClient`, `ResponseHandler` |
| **Inputs** | N/A |
| **Outputs** | Re-exported names |
| **Side effects** | None |
| **Imported by** | Unknown from static analysis (no `from ai import` hits) |
| **Imports** | `ai.agents`, `ai.client`, `ai.response.response_handler` |
| **Actively used** | Partially — consumers import submodules directly |
| **Confidence** | **High** |

### `client.py`

| | |
| --- | --- |
| **Purpose** | OpenAI chat completions with `response_format: json_object` |
| **Public** | `MissingAPIKeyError`, `LLMClient` (Protocol), `OpenAIClient`, `complete_json`, `complete_json_messages`, `from_settings` |
| **Inputs** | API key, prompts, optional message history |
| **Outputs** | `dict[str, Any]` parsed JSON |
| **Side effects** | HTTP call to OpenAI when methods invoked |
| **Imported by** | `ai/agents/base.py`, `ai/__init__.py`, `api/chat_orchestrator.py`, several agent modules and tests |
| **Imports** | `config.settings`, `openai` (lazy) |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `prompts_loader.py`

| | |
| --- | --- |
| **Purpose** | Read and cache markdown prompts from `ai/prompts/` |
| **Public** | `PROMPTS_DIR`, `load_prompt(name)`, `prompts_dir()` |
| **Inputs** | Prompt filename relative to `prompts/` |
| **Outputs** | Stripped file text |
| **Side effects** | Filesystem read; LRU cache |
| **Imported by** | `ai/agents/base.py`, `context_agent.py`, `synthesis_agent.py` |
| **Imports** | stdlib only |
| **Actively used** | `load_prompt` yes; `prompts_dir` no external callers |
| **Confidence** | **High** |

### `interaction_specs.py`

| | |
| --- | --- |
| **Purpose** | Load cached decision-mode `NodeInteractionSpec` tuples for pipe wall thickness nomenclature node |
| **Public** | `default_pipe_wall_thickness_decision_interactions()` |
| **Inputs** | None (reads `standards/asme_b31.3` via `StandardsReader`) |
| **Outputs** | `tuple[NodeInteractionSpec, ...]` |
| **Side effects** | Reads standards files; LRU cache |
| **Imported by** | `ai/input_extractor.py`, `api/chat_orchestrator.py`, `api/parameter_definitions.py` |
| **Imports** | `engine/graph/node_interaction.py`, `engine/reference/standards_reader.py` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `input_extractor.py`

| | |
| --- | --- |
| **Purpose** | Deterministic parsing of pipe wall thickness inputs from natural language |
| **Public** | `InputRejection`, `ExtractionResult`, `extract_pipe_wall_thickness_inputs()` |
| **Inputs** | User message, optional pending interactions, existing inputs, allowed fields |
| **Outputs** | `ExtractionResult` with `EngineeringInput` dict and rejections |
| **Side effects** | None |
| **Imported by** | `api/chat_orchestrator.py`, `ai/response/response_handler.py` (type only), `tests/ai/test_input_extractor.py` |
| **Imports** | `ai/interaction_specs.py`, `ai/user_response_extractor.py`, `engine/*`, `models/input.py` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `user_response_extractor.py`

| | |
| --- | --- |
| **Purpose** | Map user replies to pending graph decision/value interactions |
| **Public** | `extract_interaction_responses`, `extract_confirmation_intent`, `extract_value_override`, `confirm_proposed_input`, `resolve_pending_value_responses`, `extract_explicit_interaction_value` |
| **Inputs** | Message text, `NodeInteractionSpec` sequences, existing inputs |
| **Outputs** | `dict[str, EngineeringInput]` or bool |
| **Side effects** | None |
| **Imported by** | `ai/input_extractor.py`, `tests/ai/test_user_response_extractor.py`, `tests/graph/test_default_confirmation.py` |
| **Imports** | `engine/graph/node_interaction.py`, `models/input.py` |
| **Actively used** | All except `extract_explicit_interaction_value` |
| **Confidence** | **High** |

### `response/__init__.py`

| | |
| --- | --- |
| **Purpose** | Re-export `ResponseHandler` |
| **Public** | `ResponseHandler` |
| **Imported by** | `ai/__init__.py`, `api/chat_orchestrator.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `response/response_handler.py`

| | |
| --- | --- |
| **Purpose** | Convert agent dataclasses to user-facing strings; bridge to engine messaging builders |
| **Public** | `ResponseHandler` and format methods (`format_intent`, `format_planner`, `format_input_requests`, `format_formula_parameter_prompt`, `format_step_prompt`, `format_rejections`, `format_routing`, `format_context`, `format_synthesis`) |
| **Inputs** | `models.agent` results, optional `StandardsReader`, `Task`, `NavigationPlan`, rejections |
| **Outputs** | Formatted `str` or `None` |
| **Side effects** | Lazy imports from `engine.messaging` |
| **Imported by** | `api/chat_orchestrator.py`, `ai/__init__.py`, `tests/agents/test_synthesis_agent.py` |
| **Imports** | `models/agent.py`, `ai/input_extractor.py` (InputRejection) |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `prompts/*.md` (summary)

Prompt files are data, not executable code. Ten are loaded at runtime (see Files table). Seven appear unused by code — they may reflect an earlier multi-prompt planner design documented in `docs/core/11. planner_layer_design.md`.

---

## Related documentation

- [agents/README.md](agents/README.md) — per-agent inventory and traces
- [docs/core/6. ai_agent_design.md](../docs/core/6.%20ai_agent_design.md) — design doc (may drift from implementation)
- [Architecture Audit Progress](../docs/audit/PROGRESS.md)
