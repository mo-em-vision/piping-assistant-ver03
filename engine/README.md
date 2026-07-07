# engine/

Python engineering backend: standards knowledge loading, graph traversal, planning, validation, execution, state, reports, and dev inspection.

## Purpose

Owns all deterministic engineering behavior for Ver03. The desktop app (`desktopApp/`) calls into `api/` and `engine/`; it does not duplicate formulas, standards parsing, or workflow logic.

## Subfolders

| Folder | Responsibility |
|--------|----------------|
| [reference/](reference/README.md) | Standards nodes, SQLite caches, tables, materials, graph compile |
| [graph/](graph/README.md) | Micro-graph traversal, expansion, assumptions, navigation |
| [planner/](planner/README.md) | Navigation intelligence (`Planner`, tools) |
| [validation/](validation/README.md) | Pre-execution compliance gate |
| [executor/](executor/README.md) | Workflow/node execution, lookups, calculations |
| [state/](state/README.md) | In-memory task lifecycle and workflow adapters |
| [reports/](reports/README.md) | `ReportData` build and document rendering |
| [inspection/](inspection/README.md) | Dev-only trace, replay, integrity (gated) |
| [units/](units/README.md) | Unit IDs, registry, SI conversion |
| [equation/](equation/README.md) | SymPy evaluation and 4-step display |
| [presentation/](presentation/README.md) | Workflow UI blocks from graph + state |
| [messaging/](messaging/README.md) | Deterministic user prompts (no LLM) |
| [events/](events/README.md) | Structured execution event log |
| [execution/](execution/README.md) | Workflow lifecycle event emission |
| [rules/](rules/README.md) | Lightweight condition evaluation for nodes |

## Root files

| File | Purpose |
|------|---------|
| `__init__.py` | Re-exports `Router`, `route`, `PIPE_WALL_THICKNESS_DESIGN` |
| `router.py` | Regex workflow classification (`pipe_wall_thickness_design`, `mawp_design`); no execution |

## Entry Points

| Entry | Used by |
|-------|---------|
| `engine.router.route` | `api/chat_orchestrator.py`, `api/workflow_bootstrap.py`, tests |
| `engine.graph.GraphEngine` | Planner, executor, API bootstrap, agents |
| `engine.planner.Planner` | `ai/agents/planner_agent.py`, tests, e2e |
| `engine.executor.execute_workflow` | `api/workflow_bootstrap.py`, acceptance tests |
| `engine.state.TaskStateManager` | API, CLI, storage, tests |
| `engine.reports.ReportGenerator` | CLI reports, acceptance tests |
| `engine.reference.StandardsReader` | Nearly all layers |

## Dependencies

**Inbound:** `api/`, `ai/`, `scripts/`, `tests/`

**Outbound:** `models/` (task, execution, validation, report DTOs), `config/` (paths), `standards/` (source data on disk)

## Runtime Usage

**Active.** Primary path: user message → `api/` → `Planner` / `GraphEngine` → input collection → `ValidationEngine` → `Executor` → `TaskStateManager` → reports/presentation APIs.

Micro-graph mode is default when `StandardsReader.graph_store.available` (compiled `*_graph.db` exists).

## Possible Dead Code

| Item | Why |
|------|-----|
| `router.MAWP_DESIGN` | Routed via `IntentAgent` + `tests/api/test_mawp_*`; graph expansion in `tests/graph/test_mawp_*` |
| Legacy `depends_on` traversal in `graph_engine.py` | Gated by `VER03_LEGACY_GRAPH_TRAVERSAL`; micro-graph preferred |
| `_STUB_ROOTS` in `graph_engine.py` | `integrity_check`, `pressure_test_verification` advertised but `implemented: False` |
| `engine/units/__init__.py` | Empty `__all__`; consumers import submodules directly |

## Notes

- **Two traversal systems:** `MicroGraphEngine` + `lazy_expander` (current) vs legacy `depends_on` BFS in `graph_engine.py` (env-flagged).
- **Two parameter-registry paths:** `MicroGraphEngine.seed_parameter_registry` (current) vs deprecated `parameter_registry.seed_parameter_registry`.
- **Naming collision:** `engine/execution/` (lifecycle events) vs `engine/executor/` (node execution) — different packages.
- **Inspection is dev-only:** `DEV_INSPECTION_ENABLED=1` or unpackaged Electron dev builds.

## Execution Traces

### Desktop task (happy path)

```
desktopApp → api/desktop_service.py | api/workflow_bootstrap.py
  → StandardsReader
  → GraphEngine.build_plan / MicroGraphEngine.expand
  → Planner.plan (navigation phases, assumptions)
  → TaskStateManager (inputs/outputs)
  → ValidationEngine.validate_plan
  → Executor.execute_plan → NodeRunner → LookupEngine / sympy / functions
  → build_workflow_state → presentation_engine.build_presentation
  → api serializers → desktopApp
```

### Report generation

```
api/report_service.py | tests/e2e/scenario_runner.py
  → report_data.build_report_from_task
  → ReportGenerator.generate → formatters (md/html/json/pdf)
```

### Dev inspection

```
api/inspection.py (if inspection_enabled)
  → inspection.builder.build_inspection_payload
  → trace, replay, provenance, integrity
```
