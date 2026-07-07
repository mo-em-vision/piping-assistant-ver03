# ai/agents/ — Architecture Audit

Audited: 2026-07-01. Static analysis only; no code changes.

Parent package overview: [../README.md](../README.md).

## Purpose

`ai/agents/` contains **specialized agent classes** that combine markdown prompts (`ai/prompts/`), an optional `LLMClient`, and deterministic fallbacks from `engine/`. Each agent returns structured `models.agent` dataclasses.

Agents handle navigation intelligence (intent, planning, missing inputs, context switches), conversational assistance (task Q&A, selection explain, continuation suggestions), and report wording — not engineering execution.

## Files

| File | Role |
| --- | --- |
| `__init__.py` | Re-exports six "core" navigation agents |
| `base.py` | `BaseAgent` — prompt loading and LLM JSON completion |
| `_constants.py` | Shared pipe-wall-thickness constants, regex helpers |
| `source_utils.py` | Normalize LLM source citations for chat responses |
| `intent_agent.py` | Classify user intent (router + LLM fallback) |
| `planner_agent.py` | Build navigation plan (engine planner + LLM fallback) |
| `input_agent.py` | Identify missing inputs and build requests |
| `routing_agent.py` | Multi-standard routing (deterministic + LLM) |
| `context_agent.py` | Detect off-topic / context-switch messages |
| `synthesis_agent.py` | Enhance report markdown and section explanations |
| `task_assist_agent.py` | Task-scoped chat Q&A |
| `selection_explain_agent.py` | Explain highlighted workspace text |
| `task_continuation_agent.py` | Suggest follow-up workflows after completion |

## Entry Points

| Entry | Runnable? | Notes |
| --- | --- | --- |
| Agent class constructors | Indirect | Instantiated by orchestrator, API services, report layer, tests |
| `BaseAgent.complete_json()` / `complete_json_messages()` | Indirect | Called from agent methods when LLM path is taken |
| `fallback_suggestions()` | Indirect | Module-level helper in `task_continuation_agent.py` |

No `if __name__ == "__main__"` in this folder.

## Dependencies

### Internal

```
__init__.py           → context, input, intent, planner, routing, synthesis agents
base.py               → ai/client.py, ai/prompts_loader.py
intent_agent.py       → base, _constants, engine/router
planner_agent.py      → base, engine/planner, engine/reference, engine/state, models/*
input_agent.py        → base, _constants, engine/state, models/*
routing_agent.py      → base, _constants, engine/router
context_agent.py      → base, _constants, ai/prompts_loader
synthesis_agent.py    → base, prompts_loader, engine/reports/formatters (lazy)
task_assist_agent.py  → base, source_utils, ai/client
selection_explain_agent.py → base, source_utils, ai/client
task_continuation_agent.py → base, ai/client
```

### External

| Source | Used by |
| --- | --- |
| `engine/router.py` | `intent_agent.py`, `routing_agent.py` |
| `engine/planner/planner.py` | `planner_agent.py` |
| `engine/state/state_manager.py` | `planner_agent.py`, `input_agent.py` |
| `engine/reference/standards_reader.py` | `planner_agent.py` |
| `engine/reports/formatters.py` | `synthesis_agent.py` (lazy) |
| `models/agent.py` | All agent modules |
| `models/planning.py` | `planner_agent.py`, `input_agent.py` |
| `models/task.py` | `planner_agent.py`, `input_agent.py` |
| `models/report.py` | `synthesis_agent.py` |
| `ai/client.py` | `base.py`, assist/continuation/selection agents |
| `ai/prompts_loader.py` | `base.py`, `context_agent.py`, `synthesis_agent.py` |

### Dependents

| Consumer | Agents used |
| --- | --- |
| `api/chat_orchestrator.py` | `ContextAgent`, `InputAgent`, `IntentAgent`, `PlannerAgent`; `_constants.missing_pipe_inputs` |
| `api/chat_service.py` | `TaskAssistAgent`, `SelectionExplainAgent` |
| `api/task_continuation_service.py` | `TaskContinuationAgent` |
| `engine/reports/presentation.py` | `SynthesisAgent` |
| `ai/__init__.py` | Six core agents from `agents/__init__.py` |
| `tests/agents/*`, `tests/acceptance/`, `tests/mvp/` | Various |

`RoutingAgent` is exported but not imported by orchestrator or API services.

## Runtime Usage

| Agent | On execution path? | Evidence |
| --- | --- | --- |
| `IntentAgent` | **Yes** | `api/chat_orchestrator.py` every chat message |
| `PlannerAgent` | **Yes** | `api/chat_orchestrator.py` |
| `InputAgent` | **Yes** | `api/chat_orchestrator.py` |
| `ContextAgent` | **Yes** | `api/chat_orchestrator.py` |
| `TaskAssistAgent` | **Yes** | `api/chat_service.py` |
| `SelectionExplainAgent` | **Yes** | `api/chat_service.py` |
| `TaskContinuationAgent` | **Yes** | `api/task_continuation_service.py` |
| `SynthesisAgent` | **Conditional** | `engine/reports/presentation.py` when `use_ai=True` |
| `RoutingAgent` | **No** (runtime) | Tests and package exports only |

## Possible Dead Code

| Symbol | Why | Confidence |
| --- | --- | --- |
| `RoutingAgent` (entire class) | Not wired into orchestrator or API; `IntentAgent` + `engine.router` cover routing today | **High** |
| `RoutingAgent.record_alternative()` | No callers outside `routing_agent.py` | **High** |
| `SynthesisAgent._fallback_presentation()` | Never called | **High** |
| `ContextAgent.confirm_override()` | Returns dataclass; no callers outside `context_agent.py` | **Medium** |
| Agents in `ai/__init__.py` but not in `agents/__init__.py` | `TaskAssistAgent`, `SelectionExplainAgent`, `TaskContinuationAgent` omitted from `agents/__init__.py` — intentional split, not dead | **N/A** |

## Notes

### Agents not in `agents/__init__.py`

`TaskAssistAgent`, `SelectionExplainAgent`, and `TaskContinuationAgent` are API/desktop features imported directly from their modules. The six agents in `__init__.py` match the CLI navigation pipeline.

### Deterministic-first pattern

Most agents try rules or `engine/` delegation first, then LLM only when a client is configured and heuristics are insufficient:

| Agent | Primary path | LLM trigger |
| --- | --- | --- |
| `IntentAgent` | `engine.router.route()` | Unmatched request |
| `PlannerAgent` | `engine.planner.Planner` | `action == CLARIFY` and client present |
| `InputAgent` | `NavigationPlan` / static field lists | Client present and not deterministic phase |
| `RoutingAgent` | Keywords + `route()` | No deterministic match |
| `ContextAgent` | `CONTEXT_KEYWORDS` regex | No active task and client present |
| `SynthesisAgent` | `render_markdown()` passthrough | Client present for enhancement |
| `TaskAssistAgent` | N/A | Always LLM (graceful no-key message) |
| `SelectionExplainAgent` | N/A | Always LLM (graceful no-key message) |
| `TaskContinuationAgent` | `fallback_suggestions()` | LLM with fallback on error/no key |

### Duplicate with `engine/`

- `IntentAgent` duplicates routing concern with `RoutingAgent` (latter unused at runtime).
- `PlannerAgent` is a thin wrapper; real graph navigation is `engine.planner.Planner`.

---

## Execution traces (agent-level)

### Navigation pipeline (orchestrator)

```
ChatOrchestrator.handle_message()
    → IntentAgent.analyze()
    → PlannerAgent.plan_navigation() / plan()
    → InputAgent.analyze()
    → ContextAgent.evaluate()  [runs earlier for context-switch gate]
```

### Assist / explain (API)

```
api/chat_service.py
    → TaskAssistAgent.reply()        # chat tab
    → SelectionExplainAgent.explain()  # highlight explain
```

### Continuation

```
api/task_continuation_service.py
    → TaskContinuationAgent.suggest()
```

### Report synthesis

```
engine/reports/presentation.py
    → SynthesisAgent.enhance_engineering_report()
    → SynthesisAgent.explain_section()  # per display section
```

---

## Per-file inventory

### `__init__.py`

| | |
| --- | --- |
| **Purpose** | Export core navigation agents |
| **Public** | `ContextAgent`, `InputAgent`, `IntentAgent`, `PlannerAgent`, `RoutingAgent`, `SynthesisAgent` |
| **Imported by** | `ai/__init__.py` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `base.py`

| | |
| --- | --- |
| **Purpose** | Shared LLM prompt loading and JSON completion |
| **Public** | `BaseAgent`, `load_prompt()`, `complete_json()`, `complete_json_messages()`, `format_context()`, `client` property |
| **Inputs** | Optional `LLMClient`; subclasses set `prompt_file` |
| **Outputs** | Parsed JSON dict |
| **Side effects** | OpenAI API calls via injected or default client |
| **Imported by** | All agent modules |
| **Imports** | `ai/client.py`, `ai/prompts_loader.py` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `_constants.py`

| | |
| --- | --- |
| **Purpose** | Pipe wall thickness workflow constants and regex helpers |
| **Public** | `PIPE_WALL_THICKNESS_DESIGN`, `PIPE_WALL_THICKNESS_ROOT`, `PIPE_WALL_THICKNESS_NODE`, `REQUIRED_*` tuples, `CONTEXT_KEYWORDS`, `INSPECTION_KEYWORDS`, `MISSING_CONTEXT_PATTERNS`, `missing_pipe_inputs()`, `detect_missing_context()` |
| **Inputs** | Message string or stored inputs dict |
| **Outputs** | Lists of missing field ids |
| **Side effects** | None |
| **Imported by** | `intent_agent.py`, `input_agent.py`, `routing_agent.py`, `context_agent.py`, `api/chat_orchestrator.py` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `source_utils.py`

| | |
| --- | --- |
| **Purpose** | Normalize LLM `sources` array or fall back to retrieval sources |
| **Public** | `normalize_chat_sources(llm_sources, fallback_sources)` |
| **Inputs** | LLM JSON sources list, fallback citation dicts |
| **Outputs** | `list[dict[str, Any]]` |
| **Side effects** | None |
| **Imported by** | `task_assist_agent.py`, `selection_explain_agent.py` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `intent_agent.py`

| | |
| --- | --- |
| **Purpose** | Classify engineering intent for chat requests |
| **Public** | `IntentAgent`, `analyze(request, context)` |
| **Prompt** | `intent_agent.md` |
| **Inputs** | User message, optional `AgentContext` |
| **Outputs** | `IntentResult` |
| **Side effects** | LLM call on unmatched router path |
| **Imported by** | `api/chat_orchestrator.py`, `ai/__init__.py`, tests |
| **Imports** | `engine/router`, `models/agent`, `base`, `_constants` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `planner_agent.py`

| | |
| --- | --- |
| **Purpose** | Produce navigation plan from intent |
| **Public** | `PlannerAgent`, `plan_navigation()`, `plan()`, `_to_planner_result()` |
| **Prompt** | `planner_agent.md` (LLM fallback only) |
| **Inputs** | `IntentResult`, optional `Task`, `user_message` |
| **Outputs** | `NavigationPlan` or `PlannerResult` |
| **Side effects** | Delegates to `engine.planner.Planner`; optional LLM |
| **Imported by** | `api/chat_orchestrator.py`, `ai/__init__.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `input_agent.py`

| | |
| --- | --- |
| **Purpose** | List missing inputs and human-readable request reasons |
| **Public** | `InputAgent`, `analyze()`, `analyze_from_state()` |
| **Prompt** | `input_agent.md` (optional enrichment) |
| **Inputs** | `Task`, workflow, `AgentContext`, `NavigationPlan` |
| **Outputs** | `InputAgentResult` |
| **Side effects** | Optional LLM call |
| **Imported by** | `api/chat_orchestrator.py`, `ai/__init__.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `routing_agent.py`

| | |
| --- | --- |
| **Purpose** | Present standard options when multiple codes may apply |
| **Public** | `RoutingAgent`, `route()`, `record_alternative()` |
| **Prompt** | `routing_agent.md` |
| **Inputs** | User request string |
| **Outputs** | `RoutingResult` |
| **Side effects** | Optional LLM call |
| **Imported by** | `ai/__init__.py`, `agents/__init__.py`, tests only |
| **Actively used** | **No** on production path |
| **Confidence** | **High** |

### `context_agent.py`

| | |
| --- | --- |
| **Purpose** | Detect unrelated messages during active tasks |
| **Public** | `ContextAgent`, `evaluate()`, `confirm_override()` |
| **Prompt** | `intent_detection.md` (loaded twice on LLM path — see parent README Notes) |
| **Inputs** | Message, optional `AgentContext` |
| **Outputs** | `ContextResult` |
| **Side effects** | Optional LLM call |
| **Imported by** | `api/chat_orchestrator.py`, `ai/__init__.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `synthesis_agent.py`

| | |
| --- | --- |
| **Purpose** | AI narrative for reports without changing engineering values |
| **Public** | `SynthesisAgent`, `synthesize()`, `enhance_engineering_report()`, `explain_section()` |
| **Prompts** | `engineering_report_enhancement.md`, `report_explanation.md` |
| **Inputs** | `ReportData`, section payload dicts |
| **Outputs** | `SynthesisResult` or explanation string |
| **Side effects** | LLM calls; `ValueError` if numeric values omitted from output |
| **Imported by** | `engine/reports/presentation.py`, `ai/__init__.py`, tests |
| **Actively used** | **Yes** (when `use_ai=True`) |
| **Confidence** | **High** |

### `task_assist_agent.py`

| | |
| --- | --- |
| **Purpose** | Answer follow-up questions about an active task |
| **Public** | `TaskAssistAgent`, `TaskAssistReply`, `reply()` |
| **Prompt** | `task_assist.md` |
| **Inputs** | User message, history, context brief, standards retrieval text |
| **Outputs** | `TaskAssistReply` (reply + sources) |
| **Side effects** | LLM call; returns API-key message if unconfigured |
| **Imported by** | `api/chat_service.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `selection_explain_agent.py`

| | |
| --- | --- |
| **Purpose** | Educational explanations for user-highlighted text |
| **Public** | `SelectionExplainAgent`, `SelectionExplainReply`, `explain()` |
| **Prompt** | `selection_explanation.md` |
| **Inputs** | User prompt, history, context brief, standards retrieval |
| **Outputs** | `SelectionExplainReply` |
| **Side effects** | LLM call; API-key fallback message |
| **Imported by** | `api/chat_service.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `task_continuation_agent.py`

| | |
| --- | --- |
| **Purpose** | Suggest related workflows after task completion |
| **Public** | `TaskContinuationAgent`, `fallback_suggestions()`, `normalize_suggestions()`, `suggest()` |
| **Prompt** | `task_continuation.md` |
| **Inputs** | `context_brief`, `workflow_id` |
| **Outputs** | `list[dict[str, str]]` (id, title, description) |
| **Side effects** | LLM call with static fallbacks |
| **Imported by** | `api/task_continuation_service.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |
