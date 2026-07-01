# models/ — Architecture Audit

Audited: 2026-07-01. Static analysis only; no code changes.

## Purpose

`models/` holds **pure Python dataclasses and enums** that define shared data shapes for the engineering knowledge-graph system. These types carry no business logic (except a few small factory/helper functions in `input.py` and one property on `LayerValidationResult`). They are the contract between backend layers (`engine/`, `ai/`, `api/`, `cli/`) and serialization boundaries.

## Files

| File | Role |
| --- | --- |
| `__init__.py` | Re-exports public model symbols via `__all__` |
| `agent.py` | AI agent action enum and structured agent outputs |
| `calculation.py` | Calculation trace and quantity result types |
| `event.py` | Execution audit event types |
| `execution.py` | Execution plan, per-node results, run status |
| `graph.py` | Graph edge type enum, edges, graph version metadata |
| `input.py` |  Engineering inputs, parameter registry, resolution provenance |
| `node_documentation.py` | Resolved per-node documentation (Phase 7) |
| `node_output.py` | Named outputs from executable nodes (Phase 11) |
| `planning.py` | Planner navigation plan and workflow candidates |
| `report.py` | Report payload, traceability, display sections |
| `rule.py` | Legacy rule-validation result types |
| `standard_node.py` | Legacy standard knowledge-node schema |
| `task.py` | Task session state and input conflicts |
| `validation.py` | Validation Layer aggregated results |
| `workflow_lifecycle.py` | Graph traversal lifecycle events (Phase 8) |
| `workflow_state.py` | Mutable runtime workflow state (Phase 5+) |

## Entry Points

| Entry | Runnable? | Notes |
| --- | --- | --- |
| `models/__init__.py` | No | Package import surface; no `if __name__ == "__main__"` |
| Individual modules | No | Imported by other packages only |

Nothing in `models/` is executed as a standalone script or CLI command.

## Dependencies

### Internal (within `models/`)

```
workflow_state.py → node_documentation.py, node_output.py, workflow_lifecycle.py
execution.py      → graph.py, input.py
planning.py       → agent.py
task.py           → input.py
__init__.py       → all other model modules (partial; see Notes)
```

### External (folders/files this package imports)

| Source | Used by |
| --- | --- |
| Python stdlib (`dataclasses`, `datetime`, `enum`, `typing`) | All modules |

`models/` does **not** import from `engine/`, `api/`, `storage/`, or `ai/`.

### Dependents (who imports `models/`)

Grep (`from models.` / `import models`) found **80+** importing files across:

| Area | Examples |
| --- | --- |
| `engine/` | `executor/`, `graph/`, `state/`, `validation/`, `reports/`, `presentation/`, `planner/`, `execution/`, `inspection/`, `messaging/` |
| `ai/` | `agents/`, `response/`, `user_response_extractor.py` |
| `api/` | `desktop_service.py`, `serializers.py`, `workflow_bootstrap.py`, `report_service.py`, `output_blocks.py`, … |
| `cli/` | `session_store.py`, `commands/chat.py`, `orchestrator.py`, `display.py` |
| `storage/` | `project_session_store.py` (`Task`, `TaskStatus`) |
| `dev/` | `graph_explorer/adapter.py` |
| `tests/` | Broad coverage under `tests/api/`, `tests/engine/`, `tests/agents/`, etc. |

No TypeScript/desktop frontend imports from `models/` (backend-only).

## Runtime Usage

**Yes — actively on the execution path.**

Evidence:

1. **Task lifecycle**: `models.task.Task` / `TaskStatus` flow through `engine/state/state_manager.py` → `api/serializers.py` → desktop REST API.
2. **Graph execution**: `models.execution.ExecutionPlan` is built in `engine/graph/graph_engine.py` and consumed by `engine/executor/executor.py`.
3. **Inputs**: `models.input.EngineeringInput` is the universal input carrier across planner, executor, validation, and API layers.
4. **Workflow runtime**: `models.workflow_state.WorkflowState` is held in `engine/state/state_manager.py` and serialized to the frontend.
5. **Reports**: `models.report.ReportData` is assembled in `engine/reports/report_data.py` and returned via `api/report_service.py`.

## Possible Dead Code

| Symbol / file | Why it appears unused | Confidence |
| --- | --- | --- |
| `models/rule.py` (`RuleValidation`, `ValidationResult`) | Grep finds **no importers** outside `models/__init__.py`. Active validation uses `models/validation.py` instead. | **High** |
| `models/standard_node.py` (entire file) | Grep finds **no importers** outside `models/__init__.py`. Runtime graph uses `engine/reference/standards_reader.py` and compiled graph nodes, not this schema. | **High** |
| `models/input.py` — `InputLimits` | Defined and exported; **no external references** beyond the `EngineeringInput.limits` field. | **Medium** |
| `models/execution.py` — `ExecutionConfiguration` | Only referenced inside `ExecutionPlan` default; **no code reads or sets** `configuration` fields at runtime (grep). | **Medium** |
| `models/__init__.py` — `NodeDocumentation` in `__all__` | Listed in `__all__` but **not imported** in `__init__.py`; `from models import NodeDocumentation` would fail. Direct imports from `models.node_documentation` are active. | **High** (export bug, not dead type) |
| `models/task.py` — `TaskStatus.IN_PROGRESS` | Coexists with `ACTIVE`; usage split unknown without exhaustive enum-value grep. | **Low** |

Do not delete based on this audit alone.

## Notes

### Unusual / duplicate patterns

1. **Two validation result models**: `models/rule.py` (`ValidationResult` enum + `RuleValidation`) vs `models/validation.py` (`ComplianceStatus`, `LayerValidationResult`). Only `validation.py` is used in `engine/validation/`.
2. **Two node schemas**: `models/standard_node.py` (`StandardNode`) vs runtime graph nodes in `engine/reference/standards_reader.py` / compiled YAML graph. No bridge from `StandardNode` found.
3. **Two workflow-state modules**: `models/workflow_state.py` (data) vs `engine/state/workflow_state.py` (conversion/build helpers). Names collide; imports disambiguate by path.
4. **Edge type enum spans eras**: `models/graph.py` `EdgeType` lists legacy `dependency`/`reference` types and semantic micro-graph types (`requires`, `calculates`, …) in one enum.
5. **`InputStatus.DEFAULT_UNCONFIRMED`**: Alias to `"proposed_default"` for backward compatibility (`models/input.py` line 24).
6. **`EquationDefinition`**: Alias for `FormulaDefinition` in `standard_node.py` (unused file).
7. **`TaskStatus`**: Both `ACTIVE` and `IN_PROGRESS` exist; callers use both statuses in different code paths.
8. **No `from models import …` usage**: All consumers import submodule paths (`from models.task import Task`). Package `__init__.py` re-exports are largely unused.

---

## Per-file inventory

### `__init__.py`

| | |
| --- | --- |
| **Purpose** | Public re-export surface |
| **Public symbols** | 60+ names in `__all__` |
| **Inputs** | N/A |
| **Outputs** | Imported names |
| **Side effects** | None |
| **Imported by** | Unknown from static analysis (no direct `from models import` grep hits) |
| **Imports** | All sibling model modules |
| **Actively used** | Partially — submodule imports bypass this file |
| **Confidence** | **High** |

### `agent.py`

| | |
| --- | --- |
| **Purpose** | Structured outputs for AI agents (intent, planner, input, routing, context, synthesis) |
| **Public** | `AgentAction`, `AgentContext`, `IntentResult`, `PlannerResult`, `InputRequest`, `InputAgentResult`, `StandardOption`, `RoutingResult`, `ContextResult`, `AlternativePathRecord`, `SynthesisResult`, `OverrideConfirmation` |
| **Inputs** | Constructor/field values from agents |
| **Outputs** | Dataclass instances consumed by `ai/response/response_handler.py` |
| **Side effects** | None |
| **Imported by** | `ai/agents/*.py`, `ai/response/response_handler.py`, `engine/planner/planner.py`, `engine/planner/tools.py`, `api/workflow_bootstrap.py`, many tests |
| **Imports** | stdlib only |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `calculation.py`

| | |
| --- | --- |
| **Purpose** | Calculation engine trace structures |
| **Public** | `CalculationStatus`, `QuantityResult`, `CalculationStep`, `CalculationResult` |
| **Imported by** | `engine/executor/calculation_engine.py`, `lookup_engine.py`, `standards_equation.py`, `functions.py` |
| **Imports** | stdlib |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `event.py`

| | |
| --- | --- |
| **Purpose** | Audit log event schema |
| **Public** | `EventType`, `Event` |
| **Imported by** | `engine/events/event_logger.py` (`Event`, `EventType`); `EventType` also in `engine/executor/executor.py`, `engine/planner/planner.py`, `engine/validation/validation_engine.py`, tests |
| **Side effects** | `Event.timestamp` defaults to UTC now at construction |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `execution.py`

| | |
| --- | --- |
| **Purpose** | Execution plan and run results |
| **Public** | `NodeExecutionStatus`, `ExecutionStatus`, `ExecutionConfiguration`, `ExecutionPlan`, `NodeExecutionResult`, `ExecutionResult` |
| **Imported by** | `engine/graph/graph_engine.py`, `micro_graph_engine.py`, `engine/executor/executor.py`, `node_runner.py`, `engine/inspection/planner_decisions.py`, `engine/validation/validation_engine.py`, many tests |
| **Imports** | `models.graph`, `models.input` |
| **Actively used** | **Yes** (`ExecutionConfiguration` field usage: **Low**) |
| **Confidence** | **High** (overall); **Medium** for `ExecutionConfiguration` |

### `graph.py`

| | |
| --- | --- |
| **Purpose** | Graph edges and version snapshot |
| **Public** | `EdgeType`, `GraphEdge`, `GraphVersion` |
| **Imported by** | `engine/graph/graph_engine.py`, `micro_graph_engine.py`, `traversal.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `input.py`

| | |
| --- | --- |
| **Purpose** | Engineering input model, parameter registry, resolution provenance, helper factories |
| **Public** | `InputSource`, `InputStatus`, `ResolutionMethod`, `InputLimits`, `ResolutionRef`, `EngineeringInput`, `ParameterDescriptor`, `input_is_expansion_ready()`, `proposed_default_input()`, `pending_parameter_input()` |
| **Imported by** | Most of `engine/`, `ai/`, `api/`, `cli/session_store.py`, `storage/project_session_store.py` (indirect via cli helpers) |
| **Actively used** | **Yes**; `InputLimits` externally unused (**Medium** dead) |
| **Confidence** | **High** |

### `node_documentation.py`

| | |
| --- | --- |
| **Purpose** | Resolved documentation for one graph node (Phase 7) |
| **Public** | `NodeDocumentation` |
| **Imported by** | `engine/graph/documentation_resolver.py`, `engine/execution/lifecycle_emitter.py`, `engine/presentation/blocks.py`, `models/workflow_state.py` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `node_output.py`

| | |
| --- | --- |
| **Purpose** | Named executable-node output (Phase 11) |
| **Public** | `NodeOutput` |
| **Imported by** | `engine/state/node_outputs.py`, `engine/state/workflow_state.py`, `models/workflow_state.py` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `planning.py`

| | |
| --- | --- |
| **Purpose** | Planner navigation structures |
| **Public** | `NavigationPhase`, `StructuredIntent`, `WorkflowCandidate`, `NavigationPlan` |
| **Imported by** | `engine/planner/planner.py`, `engine/graph/workflow_navigation.py`, `navigation_phases.py`, `ai/agents/planner_agent.py`, `input_agent.py`, `engine/messaging/*`, `api/workflow_bootstrap.py`, tests |
| **Imports** | `models.agent.AgentAction` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `report.py`

| | |
| --- | --- |
| **Purpose** | Report generation payload and file-path bundle |
| **Public** | `ReportDisplaySection`, `ReportSection`, `TraceabilityEntry`, `ReportInputEntry`, `ReportTraversalStep`, `ReportDecision`, `ReportWarning`, `ReportOverride`, `ReportVersionInfo`, `ReportData`, `ReportStorage` |
| **Imported by** | `engine/reports/report_data.py`, `report_generator.py`, `formatters.py`, `block_renderer.py`, `presentation.py`, `ai/agents/synthesis_agent.py`, `api/report_service.py` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `rule.py`

| | |
| --- | --- |
| **Purpose** | Rule-level validation result (legacy) |
| **Public** | `ValidationResult`, `RuleValidation` |
| **Imported by** | `models/__init__.py` only |
| **Actively used** | **No** (appears superseded by `validation.py`) |
| **Confidence** | **High** (dead) |

### `standard_node.py`

| | |
| --- | --- |
| **Purpose** | Static standard-node schema with formulas and I/O declarations |
| **Public** | `DependencyType`, `OutputType`, `InputSourceType`, `NodeRequiredInput`, `NodeProvidedOutput`, `FormulaDefinition`, `EquationDefinition`, `StandardNode` |
| **Imported by** | `models/__init__.py` only |
| **Actively used** | **No** |
| **Confidence** | **High** (dead) |

### `task.py`

| | |
| --- | --- |
| **Purpose** | In-memory task/session unit |
| **Public** | `TaskStatus`, `InputConflict`, `Task` |
| **Imported by** | `engine/state/state_manager.py`, `api/serializers.py`, `desktop_service.py`, most API/engine modules, `storage/project_session_store.py`, tests |
| **Imports** | `models.input` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `validation.py`

| | |
| --- | --- |
| **Purpose** | Validation Layer aggregated outcomes |
| **Public** | `ComplianceStatus`, `ValidationSeverity`, `ValidationFinding`, `ValidationOverride`, `LayerValidationResult` (+ `.allowed` property) |
| **Imported by** | All `engine/validation/*.py`, `engine/executor/executor.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `workflow_lifecycle.py`

| | |
| --- | --- |
| **Purpose** | Node traversal lifecycle events (Phase 8) |
| **Public** | `WorkflowLifecycleEventType`, `WorkflowLifecycleEvent` |
| **Imported by** | `engine/execution/lifecycle_emitter.py`, `engine/presentation/blocks.py`, `models/workflow_state.py`, tests |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `workflow_state.py`

| | |
| --- | --- |
| **Purpose** | Serializable runtime workflow state separate from graph nodes |
| **Public** | `WorkflowParameter`, `WorkflowState` |
| **Imported by** | `engine/state/state_manager.py`, `engine/state/workflow_state.py`, `workflow_parameters.py`, `engine/presentation/*`, `engine/graph/doc_templates.py`, `documentation_resolver.py`, `engine/inspection/replay.py`, tests |
| **Imports** | `models.node_documentation`, `models.node_output`, `models.workflow_lifecycle` (absolute imports) |
| **Side effects** | `WorkflowState.timestamp` defaults to UTC now |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

---

## Execution traces

Traces show where `models/` types appear in real paths. Arrows use actual module/file names.

### Trace 1 — Desktop user starts / continues a task

```
Electron UI (desktopApp/)
    ↓ HTTP
api/server.py
    ↓
api/desktop_service.py
    ↓ load/save
storage/project_session_store.py  →  cli/session_store._task_from_dict / _task_to_dict
    ↓
models/task.Task, models/input.EngineeringInput  (deserialized)
    ↓
engine/state/state_manager.py  (TaskStateManager)
    ↓
api/serializers.py  →  task_state()  →  JSON to frontend
```

### Trace 2 — User message → planner → execution

```
api/chat_service.py  →  cli/orchestrator.py (ChatOrchestrator)
    ↓
ai/agents/intent_agent.py  →  models/agent.IntentResult
    ↓
engine/planner/planner.py  →  models/planning.NavigationPlan, models/event.EventType
    ↓
engine/graph/graph_engine.py  →  models/execution.ExecutionPlan, models/graph.GraphEdge
    ↓
engine/executor/executor.py  →  models/execution.ExecutionResult, models/event.EventType
    ↓
engine/state/state_manager.py  →  models/task.Task updated; models/workflow_state.WorkflowState
    ↓
storage/project_session_store.py.save_state_manager  →  persist Task JSON
```

### Trace 3 — Parameter input from UI

```
api/parameter_definitions.py  (submit_task_input)
    ↓
models/input.EngineeringInput  (status/source updates)
    ↓
engine/validation/input_validator.py  →  models/validation.LayerValidationResult
    ↓
engine/state/state_manager.py
    ↓
api/serializers.py
```

### Trace 4 — Report generation

```
api/desktop_service.py.generate_task_report
    ↓
api/report_service.py
    ↓
engine/reports/report_data.py  →  models/report.ReportData (+ nested types)
    ↓
engine/reports/report_generator.py  →  models/report.ReportStorage
    ↓
storage/project_repository.save_task_artifact  (report metadata in SQLite)
    ↓
Filesystem under sessions/<project_id>/reports/
```

### Trace 5 — Presentation / workflow state to UI

```
engine/executor/node_runner.py  →  models/execution.NodeExecutionResult
    ↓
engine/state/workflow_state.py  →  models/workflow_state.WorkflowState
    ↓
engine/presentation/presentation_engine.py
    ↓
api/output_blocks.py  →  models/task.Task
    ↓
api/serializers.task_state  →  frontend blocks
```

### Trace 6 — CLI-only path (no SQLite)

```
cli/commands/chat.py
    ↓
cli/session_store.SessionStore  (filesystem only)
    ↓
models/task.Task, models/input.EngineeringInput
    ↓
(same engine/planner/executor stack as Trace 2)
```

### Trace 7 — Audit events

```
engine/planner/planner.py  or  engine/executor/executor.py
    ↓
engine/events/event_logger.py  →  models/event.Event, EventType
    ↓
models/execution.ExecutionResult.events  (dicts via to_dicts())
```

Multiple paths exist for persistence (Trace 1 vs Trace 6) and for validation result types (`validation.py` active vs `rule.py` unused). Document only; no recommendation.
