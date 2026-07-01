# `tests/` — Architecture Audit (structure level)

Python backend and integration test suite for Ver03. Discovered and run via root `pytest.ini` (`testpaths = tests`). **Frontend tests live separately** under `desktopApp/tests/` (Vitest/Playwright) and are not part of this tree.

**Audit date:** structure-level inventory from directory listing and static grep (not line-by-line per test file).

---

## Layer mapping (subfolder → application code)

| Subfolder | Application layer(s) validated | Primary packages |
| --- | --- | --- |
| `api/` | Desktop REST API surface | `api/` |
| `engine/` | Workflow state, chat/step prompts | `engine/state/`, `engine/messaging/` |
| `graph/` | Standards graph compilation & traversal | `engine/graph/` |
| `planner/` | Task navigation & planning | `engine/planner/` |
| `executor/` | Workflow execution, lookups, MAWP | `engine/executor/` |
| `calculation/` | SymPy calculation engine & equation suites | `engine/executor/calculation_engine` |
| `validation/` | Compliance & unit validation | `engine/validation/` |
| `reference/` | Standards reader, pack DBs, resolvers | `engine/reference/` |
| `reports/` | Report generation & formatting | `engine/reports/` |
| `presentation/` | Workflow presentation payloads | `engine/presentation/` |
| `equation/` | LaTeX/equation step rendering | `engine/equation/` |
| `rules/` | Rule expression evaluation | `engine/rules/` |
| `units/` | Unit registry & conversion | `engine/units/` |
| `state/` | Node output aggregation | `engine/state/node_outputs` |
| `storage/` | SQLite desktop persistence | `storage/` |
| `ai/` | Deterministic input/response extractors | `ai/` (non-LLM paths) |
| `agents/` | LLM agent behavior (mocked client) | `ai/agents/` |
| `execution/` | Inspection trace & lifecycle events | `engine/executor/`, inspection hooks |
| `integrity/` | Graph integrity checks (dev inspection) | `engine/inspection/integrity` |
| `config/` | Settings & desktop user-data paths | `config/` |
| `cli/` | Typer CLI entry | `cli/` |
| `dev/` | Developer Graph Explorer adapter | `dev/graph_explorer/` |
| `e2e/` | Full backend pipeline scenarios | Cross-cutting (`engine/*`, `models/`) |
| `acceptance/` | MVP acceptance criteria (doc-driven) | Cross-cutting + `docs/tests/2.*` |
| `mvp/` | MVP test strategy (doc-driven) | Cross-cutting + `api/`, `docs/tests/3.*` |
| *(root)* | Release/repo health gates | `desktopApp/`, `api/server.py`, `.cursor/` |

---

## Pytest configuration & invocation

### Configuration

- **`pytest.ini`** (repo root): `testpaths = tests`, `python_files = test_*.py`
- **Markers declared** (not applied in test modules via `@pytest.mark.*` — organization is by folder instead):
  - `acceptance` → `docs/tests/2. acceptance_criteria.md`
  - `mvp` → `docs/tests/3. mvp_test_strategy.md`
  - `e2e` → `docs/tests/1. end_to_end_test_cases.md`

### Execution trace (typical `python -m pytest`)

```
shell: python -m pytest [path] [options]
    ↓
pytest loads pytest.ini (testpaths=tests)
    ↓
recursive discovery: tests/**/test_*.py
    ↓
conftest.py chain (parent → child):
    tests/conftest.py          → project_root fixture
    tests/<area>/conftest.py   → area fixtures (see Entry Points)
    ↓
test module import → fixtures resolved → test run
    ↓
assertions / pytest.raises / parametrized cases
```

### Common entry commands (from repo docs / scripts)

| Command | What runs |
| --- | --- |
| `python -m pytest tests/ -q` | Full backend suite (`README.md`) |
| `python -m pytest tests/api` | API layer (primary backend gate per `AGENTS.md`) |
| `python -m pytest tests/mvp/test_desktop_mvp_workflow.py -q` | Desktop MVP smoke (paired with frontend in `verify:mvp`) |
| `python -m pytest tests/test_release_readiness.py tests/test_cursor_rules.py -q` | Release gate (`verify:release`) |
| `cd desktopApp && npm run verify:mvp` | Frontend integration tests + `tests/mvp/test_desktop_mvp_workflow.py` |
| `cd desktopApp && npm run verify:release` | typecheck + verify:mvp + release readiness tests |

Targeted subsets are also documented in `docs/developer_inspection_framework.md`, `docs/node_dev_studio.md`, and `dev/graph_explorer/README.md`.

---

## Root (`tests/`)

### Purpose

Repository-wide pytest bootstrap and non-layer release/repo checks.

### Files

| File | Role |
| --- | --- |
| `conftest.py` | Shared `project_root` fixture |
| `test_release_readiness.py` | MVP sign-off checks: Electron scripts, builder config, health endpoint, diagnostics |
| `test_cursor_rules.py` | Verifies `AGENTS.md` and `.cursor/rules/*.mdc` exist and are configured |

### Entry Points

- `conftest.py` — loaded for all tests under `tests/`
- `test_release_readiness.py`, `test_cursor_rules.py` — direct pytest targets for release pipeline

### Dependencies

- Reads `desktopApp/package.json`, `api/server.py`, `docs/desktopApp/`, `.cursor/rules/`
- No imports from `engine/` in release tests (filesystem assertions only)

### Runtime Usage

- **`test_release_readiness.py`**, **`test_cursor_rules.py`**: part of `npm run verify:release`
- **`conftest.py`**: always loaded during pytest collection under `tests/`

### Notes

- `project_root` fixture is duplicated in several subfolder `conftest.py` files (same `parents[2]` pattern).

---

## `api/` (36 `test_*.py` modules)

### Purpose

Validates the **desktop REST API layer**: `DesktopApiService`, serializers, workflow bootstrap, chat, projects/sessions, standards browse, material catalog, MAWP workflow, dev studio CRUD/validation/search/import, inspection API, and error catalog.

### Files (by theme)

| Theme | Modules |
| --- | --- |
| Projects & sessions | `test_projects_api.py`, `test_project_delete.py`, `test_task_delete.py`, `test_recent_tasks.py`, `test_rename.py` |
| Workflow & task state | `test_workflow_execution.py`, `test_workflow_state_api.py`, `test_workflow_timeline.py`, `test_mawp_workflow.py`, `test_task_continuation.py` |
| Inputs & parameters | `test_parameter_definitions.py`, `test_parameter_edit.py`, `test_coefficient_lookup.py`, `test_allowable_stress_resolution.py`, `test_nps_input_resolution.py` |
| Node display & provenance | `test_node_activation.py`, `test_node_context.py`, `test_node_provenance.py`, `test_node_calculation_summaries.py`, `test_output_blocks.py`, `test_equation_inputs_display.py` |
| Standards & tables | `test_standards_browse.py`, `test_standards_retrieval.py`, `test_table_context.py`, `test_material_catalog.py`, `test_material_catalog_service.py` |
| Chat | `test_chat_api.py`, `test_chat_context.py` |
| Reports | `test_report_api.py` |
| Dev studio | `test_dev_studio_crud.py`, `test_dev_studio_validation.py`, `test_dev_studio_search.py`, `test_dev_studio_import.py` |
| Inspection | `test_inspection_api.py` |
| Infrastructure | `test_serializers.py`, `test_json_encoding.py`, `test_error_catalog.py` |
| `conftest.py` | `DesktopApiService`, `StandardsReader`, `TaskStateManager`, `api_session_id()` helper |

### Entry Points

- `conftest.py` — API test fixtures
- Individual `test_*.py` modules (no package `__init__.py`)

### Dependencies

- **Imports:** `api/`, `config/`, `engine/reference/`, `engine/state/`, `models/`
- **Test helpers:** `tests/acceptance/helpers.py` (workflow completion in several API tests)
- **Consumed by:** CI, `AGENTS.md` backend gate, dev studio docs

### Runtime Usage

Exercises code paths used by Electron renderer via HTTP — same service layer as `api/server.py` child process.

### Notes

- Largest single test area (~36 modules). Primary regression surface for desktop ↔ backend contract.

---

## `engine/`

### Purpose

Tests **engine subsystems not covered by dedicated sibling folders** — workflow state serialization boundary and **messaging/prompt** construction.

### Files

| Path | Role |
| --- | --- |
| `test_workflow_state.py` | Runtime `WorkflowState` JSON boundary after execution |
| `messaging/test_prompt_format.py` | Prompt formatting utilities |
| `messaging/test_step_prompt.py` | Step-level prompt assembly |
| `messaging/test_formula_parameter_prompt.py` | Formula parameter prompts |

### Entry Points

- No `conftest.py`; uses root `project_root` where needed
- `test_workflow_state.py` imports `tests.acceptance.helpers.sample_inputs`

### Dependencies

- `engine/state/`, `engine/messaging/`, `engine/executor/`, `api/json_encoding`
- Overlaps conceptually with `tests/state/` (node outputs) and `tests/graph/` (graph engine)

### Runtime Usage

Messaging tests support chat/LLM prompt paths. Workflow state test validates data shape sent toward API serializers.

---

## `graph/` (15 modules)

### Purpose

Validates **`engine/graph/`**: graph engine, store, traversal, node types, relationships, assumptions, SymPy evaluator, documentation resolver, workflow navigation, param priority.

### Files

`test_graph_engine.py`, `test_graph_store.py`, `test_graph_traversal.py`, `test_node_types.py`, `test_node_interaction.py`, `test_relationship_resolver.py`, `test_relationship_metadata.py`, `test_definition_equations.py`, `test_documentation_resolver.py`, `test_assumption_checker.py`, `test_default_confirmation.py`, `test_doc_templates.py`, `test_param_priority.py`, `test_sympy_evaluator.py`, `test_workflow_navigation.py`

### Entry Points

- No local `conftest.py`; several modules use `tests.acceptance.helpers` fixtures indirectly via imported helpers

### Dependencies

- `engine/graph/`, `engine/reference/standards_reader`, `models/`
- Shared helpers from `tests/acceptance/helpers.py`

### Runtime Usage

Core path: Planner/executor both depend on graph engine — failures here block all workflows.

---

## `planner/` (2 modules)

### Purpose

Validates **`engine/planner/`** — navigation plans, planner decisions (including inspection metadata).

### Files

`test_planner.py`, `test_planner_decisions.py`, `__init__.py`

### Dependencies

- `engine/planner/`, `engine/reference/`, `engine/state/`, `models/`

### Runtime Usage

Upstream of executor in workflow pipeline; referenced by acceptance, e2e, and mvp tests.

---

## `executor/` (8 modules)

### Purpose

Validates **`engine/executor/`** — workflow execution, lookup engine, pipe dimensions/schedules, material properties, NPS resolution, MAWP calculation and geometry.

### Files

`test_executor.py`, `test_lookup_engine.py`, `test_pipe_dimension_lookup.py`, `test_pipe_schedule_recommendation.py`, `test_material_properties_lookup.py`, `test_nps_diameter_resolution.py`, `test_mawp_calculation.py`, `test_mawp_geometry_resolver.py`, `__init__.py`

### Dependencies

- `engine/executor/`, `engine/reports/`, `engine/reference/`, `engine/state/`, `models/`

### Runtime Usage

Central execution layer between graph plans and task outputs/reports.

---

## `calculation/` (2 modules)

### Purpose

Validates **`engine/executor/calculation_engine`** and ASME **302.3.5** equation regression.

### Files

`test_calculation_engine.py`, `test_302_3_5_equations.py`

### Dependencies

- `engine/executor/calculation_engine`, `engine/executor/unit_manager`

### Notes

Narrower than `executor/` — focused on numeric/symbolic calculation correctness.

---

## `validation/` (2 modules)

### Purpose

Validates **`engine/validation/`** — validation engine and unit validator registry.

### Files

`test_validation_engine.py`, `test_unit_validator_registry.py`, `__init__.py`

### Dependencies

- `engine/validation/`, `tests/acceptance/helpers` (`sample_inputs`)

---

## `reference/` (13 modules)

### Purpose

Validates **`engine/reference/`** — standards reader, pack/node/task/config DB resolution, material & coefficient resolvers, nomenclature, pipe dimensions, formula display, DB build scripts.

### Files

`test_standards_reader_db.py`, `test_standards_reader_paths.py`, `test_standards_paths.py`, `test_standards_nodes_db.py`, `test_standards_tasks_db.py`, `test_standards_config_db.py`, `test_build_standards_nodes_db.py`, `test_material_catalog_db.py`, `test_material_resolver.py`, `test_coefficient_resolver.py`, `test_nomenclature_resolver.py`, `test_pipe_dimensions_db.py`, `test_formula_display.py`

### Dependencies

- `engine/reference/`, `standards/` tree on disk, compiled `*_graph.db` caches

### Runtime Usage

Standards micro-graph load path: Markdown/YAML → GraphBuilder → PackGraph (see `AGENTS.md`). These tests guard reference data and DB resolution.

---

## `reports/` (4 modules)

### Purpose

Validates **`engine/reports/`** — report generator, block renderer, formatters, number formatting.

### Files

`test_report_generator.py`, `test_block_renderer.py`, `test_formatters.py`, `test_number_format.py`

### Dependencies

- `engine/reports/`; `test_formatters.py` uses `tests.acceptance.helpers.run_completed_workflow`

---

## `presentation/` (1 module)

### Purpose

Validates **`engine/presentation/presentation_engine`** — UI-oriented presentation payloads from workflow state.

### Files

`test_presentation_engine.py`

### Dependencies

- `engine/presentation/`, `engine/state/workflow_state`, `tests/acceptance/helpers`

---

## `equation/` (1 module)

### Purpose

Validates **`engine/equation/equation_renderer`** — LaTeX substitution and step rendering.

### Files

`test_equation_renderer.py`

---

## `rules/` (1 module)

### Purpose

Validates **`engine/rules/rule_engine`** — conditional expressions and validation helpers.

### Files

`test_rule_engine.py`

---

## `units/` (2 modules)

### Purpose

Validates **`engine/units/`** — `UnitRegistry`, `UnitResolver`, reset hooks for test isolation.

### Files

`test_unit_registry.py`, `test_unit_resolver.py`

---

## `state/` (1 module)

### Purpose

Validates **`engine/state/node_outputs`** — per-node output aggregation after execution.

### Files

`test_node_outputs.py`

### Dependencies

- `engine/state/node_outputs`, `api/json_encoding`, `tests/acceptance/helpers`

### Notes

Complements `engine/test_workflow_state.py` (workflow-level vs node-level outputs).

---

## `storage/` (2 modules)

### Purpose

Validates **`storage/`** — `DesktopDatabase`, project repository, session store, legacy migration, standards tables.

### Files

`test_desktop_database.py`, `test_standards_tables.py`

### Dependencies

- `storage/*`, `engine/state/state_manager` (integration)

### Runtime Usage

Persistence layer for desktop projects/tasks; uses `tmp_path` for isolated SQLite files.

---

## `ai/` (2 modules)

### Purpose

Validates **deterministic `ai/` extractors** (no live LLM): chat input parsing and user response extraction.

### Files

`test_input_extractor.py`, `test_user_response_extractor.py`

### Dependencies

- `ai/input_extractor`, `ai/user_response_extractor`, `engine/graph/node_interaction`, `models/input`

### Notes

Distinct from `agents/` which tests LLM agent classes with `FakeLLMClient`.

---

## `agents/` (8 modules + conftest)

### Purpose

Validates **`ai/agents/`** behavior with a **fake LLM client** — intent, input, planner, synthesis, routing, selection explain, task assist, task continuation.

### Files

`test_intent_agent.py`, `test_input_agent.py`, `test_planner_agent.py`, `test_synthesis_agent.py`, `test_routing_context_agents.py`, `test_selection_explain_agent.py`, `test_task_assist_agent.py`, `test_task_continuation_agent.py`, `conftest.py` (`FakeLLMClient`)

### Dependencies

- `ai/agents/`, `ai/client`, `engine/router`, `models/`

### Runtime Usage

Guards agent prompt/response contracts; does not call OpenAI in tests.

---

## `execution/` (2 modules)

### Purpose

Validates **execution observability** — inspection-enriched traces and lifecycle event emission.

### Files

`test_inspection_trace.py`, `test_lifecycle_emitter.py`

### Dependencies

- `engine/executor/`, `DEV_INSPECTION_ENABLED` env toggle, `tests/acceptance/helpers`

### Runtime Usage

Supports Developer Inspector feature (`docs/developer_inspection_framework.md`).

---

## `integrity/` (1 module + conftest)

### Purpose

Validates **`engine/inspection/integrity`** graph integrity checks (rename, move, disable scenarios).

### Files

`test_graph_integrity.py`, `conftest.py`, `__init__.py`

### Entry Points

- `conftest.py` — `standards_reader` (relies on root `project_root` fixture)

### Dependencies

- `engine/inspection/integrity`, `engine/reference/standards_reader`

---

## `config/` (2 modules)

### Purpose

Validates **`config/`** — settings loading and desktop user-data directory resolution.

### Files

`test_settings.py`, `test_desktop_user_data.py`

---

## `cli/` (6 modules)

### Purpose

Validates **`cli/`** Typer application — task list, node inspect/validate, orchestrator, session store, config, chat startup, standards reader wiring.

### Files

`test_app.py`, `test_orchestrator.py`, `test_session_store.py`, `test_config.py`, `test_chat_startup.py`, `test_standards_reader.py`

### Dependencies

- `cli/app`, `typer.testing.CliRunner`

### Runtime Usage

CLI is a separate entry from desktop Electron; smoke-tested for engineering node commands.

---

## `dev/` (2 modules)

### Purpose

Validates **`dev/graph_explorer/`** — adapter subgraph building and analysis helpers (development-only tool).

### Files

`test_graph_explorer_adapter.py`, `test_graph_explorer_analysis.py`, `__init__.py`

### Dependencies

- `dev/graph_explorer/adapter`, `dev/graph_explorer/serializer`, `config/`

### Runtime Usage

Not on desktop release path; used when Graph Explorer dev server is running (`dev/graph_explorer/`).

---

## `e2e/` (2 test modules + infrastructure)

### Purpose

**End-to-end backend pipeline** tests: YAML scenarios drive planner → graph → validation → executor → report. Node schema smoke tests for standards graph shape.

### Files

| File | Role |
| --- | --- |
| `test_scenarios.py` | Parametrized scenarios from `tests/data/scenarios/*.yaml` |
| `test_node_schema.py` | Root/calculation/lookup node schema parametrized checks |
| `scenario_loader.py` | YAML → `Scenario` dataclass |
| `scenario_runner.py` | Full pipeline runner + snapshot assertions |
| `assertions.py` | Shared expected-state assertions (status, outputs, compliance) |
| `conftest.py` | `scenarios_dir`, `expected_dir`, `scenario_runner` |
| `__init__.py` | Package marker |

### Entry Points

- `conftest.py`, `scenario_runner.py`, `scenario_loader.py` — imported by acceptance and mvp suites
- `test_scenarios.py`, `test_node_schema.py` — direct pytest entry

### Dependencies

- Full `engine/*` stack, `models/`, `tests/data/scenarios/`, `tests/data/expected/`
- **Cross-test consumers:** `acceptance/conftest.py`, `mvp/conftest.py`, `mvp/test_strategy_meta.py`

### Runtime Usage

Closest automated analogue to a user completing a workflow without Electron UI.

### Notes

- **`tests/data/`**: Referenced by conftest paths and `test_scenarios.py` glob; **no YAML files found in workspace at audit time** — `test_scenarios.py` and scenario-discovery tests may fail until data is present. **Unknown from static analysis** whether data is generated, gitignored elsewhere, or pending check-in.
- `pytest.ini` marker `e2e` is declared but not applied via `@pytest.mark.e2e` on modules.

---

## `acceptance/` (12 test modules + helpers)

### Purpose

**Doc-driven MVP acceptance criteria** (`docs/tests/2. acceptance_criteria.md`) — cross-cutting proofs for workflow, graph/planner, validation, reports, reproducibility, logging, AI boundary, interface, standards/nodes, thresholds, state/storage.

### Files

| File | Role |
| --- | --- |
| `helpers.py` | **Central workflow helper library** — sample inputs, `run_completed_workflow`, report rebuild, pipe thickness intent/plan |
| `conftest.py` | `standards_reader`, `state_manager`, `expected_dir`, `scenario_runner` |
| `test_mvp_workflow.py` | §1–§2, §25 checklist parametrized criteria |
| `test_graph_and_planner.py` | Graph & planner acceptance |
| `test_validation_and_safety.py` | Validation & safety |
| `test_calculation_trace.py` | Calculation traceability |
| `test_reports_and_audit.py` | Reports & audit trail |
| `test_reproducibility.py` | Deterministic replay |
| `test_state_and_storage.py` | State persistence |
| `test_standards_and_nodes.py` | Standards pack & node presence |
| `test_interface.py` | Public interface contracts |
| `test_logging.py` | Logging behavior |
| `test_thresholds.py` | Numeric thresholds (uses e2e scenario loader) |
| `test_ai_boundary.py` | AI vs engineering boundary |
| `__init__.py` | Package marker |

### Entry Points

- **`helpers.py`** — heavily imported across `api/`, `graph/`, `mvp/`, `engine/`, `state/`, `validation/`, `reports/`
- `conftest.py` — acceptance fixture chain

### Dependencies

- Most `engine/*` layers, `tests/e2e/scenario_runner`, `tests/e2e/scenario_loader`
- Mapped to acceptance criteria document sections (referenced in module docstrings)

### Runtime Usage

Defines shared workflow completion pattern used as integration glue across the suite.

### Notes

- **De facto shared test library** — `acceptance/helpers.py` is a cross-cutting dependency, not only used by acceptance tests.

---

## `mvp/` (12 test modules + regression helper)

### Purpose

**MVP test strategy** (`docs/tests/3. mvp_test_strategy.md`) — desktop workflow smoke, determinism, regression, performance, security, conversation/state lifecycle, component strategy, failures/recovery, report comparison, strategy meta-checks.

### Files

| File | Role |
| --- | --- |
| `conftest.py` | `mvp_service` (`DesktopApiService` + tmp sessions), data dir fixtures, `scenario_runner` |
| `regression.py` | Expected output loading, wall-thickness formula regression asserts |
| `test_desktop_mvp_workflow.py` | **Primary desktop MVP gate** (roadmap §15) via `DesktopApiService` |
| `test_component_strategy.py` | §7 per-layer component tests (graph, planner, validation, report) |
| `test_calculation_regression.py` | Numeric regression vs expected JSON |
| `test_deterministic_and_graph_regression.py` | Determinism & graph regression |
| `test_report_comparison.py` | HTML/Markdown report comparison |
| `test_conversation_lifecycle.py` | Chat/conversation lifecycle |
| `test_state_lifecycle.py` | Task state transitions |
| `test_failures_and_recovery.py` | Failure/recovery scenarios (parametrized) |
| `test_performance.py` | Performance thresholds |
| `test_security.py` | Security-related checks |
| `test_node_and_standard_content.py` | Active node content presence |
| `test_strategy_meta.py` | Meta-validation of strategy artifacts & scenario discovery |
| `__init__.py` | Package marker |

### Entry Points

- **`test_desktop_mvp_workflow.py`** — invoked by `npm run verify:mvp` and `AGENTS.md`
- `conftest.py`, `regression.py` — shared by mvp modules

### Dependencies

- `api/desktop_service`, `config/`, `tests/acceptance/helpers`, `tests/e2e/*`, `tests/data/*`

### Runtime Usage

Primary release verification layer together with `desktopApp/tests/integration/*`.

---

## Shared / external test assets

### `tests/data/` (expected layout)

Referenced paths (from conftest and tests):

- `tests/data/scenarios/*.yaml` — e2e/mvp scenario definitions
- `tests/data/expected/` — golden expected outputs for regression

**Status at audit:** directory contents **not present** in workspace static listing. Tests that glob or load these paths may error until populated.

### Frontend tests (outside `tests/`)

| Location | Runner | Layer |
| --- | --- | --- |
| `desktopApp/tests/` | Vitest (`npm run test:run`) | React components, stores, utils |
| `desktopApp/tests/integration/` | Vitest | Engineering workflow integration |
| `desktopApp/tests/e2e/` | Playwright (`engineeringWorkflow.spec.ts`) | Packaged app E2E |

---

## Cross-folder dependency graph (test infrastructure)

```
tests/acceptance/helpers.py  ←── widely imported (api, graph, mvp, engine, state, validation, reports)
tests/e2e/scenario_runner.py ←── acceptance/conftest, mvp/conftest, mvp/test_strategy_meta
tests/e2e/scenario_loader.py ←── e2e/test_scenarios, acceptance/test_thresholds, mvp/test_strategy_meta
tests/e2e/assertions.py      ←── scenario_runner, mvp/test_strategy_meta
tests/mvp/regression.py      ←── mvp calculation/report regression tests
```

---

## Possible dead / dormant artifacts (structure level)

| Item | Observation | Confidence |
| --- | --- | --- |
| Pytest markers `acceptance`, `mvp`, `e2e` | Declared in `pytest.ini`; no `@pytest.mark.acceptance` / `mvp` / `e2e` found in `tests/` | High |
| `tests/data/**` | Referenced by multiple modules; no scenario YAML found at audit | Medium (may exist at runtime/CI only) |
| `cli/` tests vs desktop path | CLI tested separately; desktop uses Electron + API — parallel entry points | High (intentional, not dead) |

---

## Duplicate / overlapping coverage (documented only)

| Area | Folders involved | Notes |
| --- | --- | --- |
| Workflow completion | `acceptance/`, `mvp/`, `e2e/`, some `api/` | All exercise pipe wall thickness (and related) flows at different depths |
| Planner | `planner/`, `acceptance/test_graph_and_planner.py`, `mvp/test_component_strategy.py` | Unit vs acceptance vs strategy layers |
| Graph engine | `graph/`, `acceptance/`, `mvp/`, `e2e/test_node_schema.py` | Unit tests plus integrated scenarios |
| Reports | `reports/`, `acceptance/test_reports_and_audit.py`, `mvp/test_report_comparison.py` | Formatter/unit vs audit vs golden comparison |
| Workflow state | `engine/test_workflow_state.py`, `state/test_node_outputs.py`, `api/test_workflow_state_api.py` | Engine boundary vs node outputs vs API serialization |

---

## Related documentation

- `docs/tests/1. end_to_end_test_cases.md` — e2e scenario catalog
- `docs/tests/2. acceptance_criteria.md` — acceptance test mapping
- `docs/tests/3. mvp_test_strategy.md` — MVP strategy mapping
- `AGENTS.md` — verification commands
- `desktopApp/package.json` — `verify:mvp`, `verify:release` scripts
