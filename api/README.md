# `api/` — Architecture Audit

Audit date: 2026-07-01. Documents the HTTP API layer as it exists today (36 Python files). See [Architecture Audit Mode](../docs/todo/Architecture%20Audit%20Mode.md).

---

## Purpose

The `api/` package is the **desktop application's REST boundary**. It exposes a stdlib `HTTPServer` (`server.py`), routes HTTP to `DesktopApiService`, and assembles JSON payloads for the Electron client. Engineering logic lives in `engine/`, `storage/`, and `ai/`; this layer orchestrates those modules, serializes task state, and gates development-only features (Developer Inspection).

---

## Entry Points

| Entry | How started | Role |
|-------|-------------|------|
| `python -m api.server` | Electron `backendProcess.ts` spawns this; also manual dev | Full REST API on `BACKEND_HOST`:`BACKEND_PORT` (default `127.0.0.1:8000`) |
| `python -m api.health_server` | **Not referenced** by Electron or scripts | Standalone `/health` only — see [Possible Dead Code](#possible-dead-code) |
| `DesktopApiService.from_project_root()` | Constructed by `server.main()` and tests | Service layer used directly in `tests/api/` without HTTP |

`api/__init__.py` is a package marker only (one-line docstring).

---

## Runtime Usage

**Active in production desktop path:**

```
Electron main (backendProcess.ts)
  → spawn: python -m api.server
  → env: BACKEND_HOST, BACKEND_PORT, PROJECT_ROOT, DESKTOP_USER_DATA
  → optional: DEV_INSPECTION_ENABLED=1 (dev Electron)
  → ApiHandler.do_* → DesktopApiService → engine/storage/ai
  → desktopApp/src/services/api/* (fetch via BackendClient)
```

Evidence: `desktopApp/electron/services/backendProcess.ts` line 140 (`spawn(python, ['-m', 'api.server'], …)`), health check against `/health` in `server.py`.

**Also used without HTTP:** `tests/api/*`, `tests/mvp/test_desktop_mvp_workflow.py` import `DesktopApiService` directly.

---

## Dependencies (outbound)

| Area | Packages / modules |
|------|-------------------|
| Config | `config.loader.CLIConfig` |
| CLI / sessions | `cli.session_store`, `cli.orchestrator`, `cli.responses` |
| Engine | `engine.router`, `engine.graph.*`, `engine.executor.*`, `engine.planner.*`, `engine.reference.*`, `engine.reports.*`, `engine.inspection.*`, `engine.state.*` |
| Models | `models.task`, `models.input`, `models.report`, `models.agent`, `models.planning` |
| Storage | `storage.project_repository`, `storage.project_session_store`, `storage.migrate_legacy_sessions` |
| AI | `ai.agents.*` (chat, continuation) |
| Internal | `api.*` submodules (serializers, output_blocks, inspection, …) |

## Dependents (inbound)

| Consumer | Imports |
|----------|---------|
| `desktopApp/electron/services/backendProcess.ts` | Spawns `api.server` (no Python import) |
| `desktopApp/src/services/api/*` | HTTP client only |
| `tests/api/*`, `tests/mvp/*` | `DesktopApiService`, individual helpers |
| `engine/reports/report_data.py` | `api.output_blocks.build_display_outputs` |
| `engine/inspection/provenance.py` | `api.node_provenance`, `api.output_blocks` |
| `engine/executor/executor.py` | `api.inspection.persist_replay_snapshot` (lazy) |
| `engine/inspection/builder.py` | `api.json_encoding.json_safe` |

---

## REST Routes (`server.py`)

All JSON responses use CORS `Access-Control-Allow-Origin: *`. Errors return `{"error": {code, message, details, recovery}}` via `error_catalog.enrich_api_error_payload`. Most task/project routes require `?session_id=<project_id>` (validated in `DesktopApiService._store_for`).

### Health

| Method | Path | Handler |
|--------|------|---------|
| GET | `/health` | `{"status":"ok"}` |
| OPTIONS | `*` | CORS preflight (204) |

### Workflows & graph

| Method | Path | `DesktopApiService` method |
|--------|------|---------------------------|
| GET | `/api/v1/workflows` | `list_workflows()` |
| GET | `/api/v1/graph/neighbors?nodeId=&depth=` | `get_graph_neighbors()` |

### Projects

| Method | Path | Method |
|--------|------|--------|
| GET | `/api/v1/projects` | `list_projects()` |
| POST | `/api/v1/projects` | `create_project(name)` |
| GET | `/api/v1/projects/{id}` | `get_project(id)` |
| PATCH | `/api/v1/projects/{id}` | `rename_project(id, name)` |
| DELETE | `/api/v1/projects/{id}` | `delete_project(id)` |
| POST | `/api/v1/projects/{id}/activate` | `activate_project(id)` → `{project, session_id}` |

### Tasks

| Method | Path | Method |
|--------|------|--------|
| GET | `/api/v1/tasks?session_id=` | `list_tasks()` |
| POST | `/api/v1/tasks?session_id=` | `create_task(workflow_id)` |
| GET | `/api/v1/recent-tasks` | `list_recent_tasks_global()` |
| GET | `/api/v1/tasks/{id}?session_id=` | `get_task()` → full `task_state` |
| PATCH | `/api/v1/tasks/{id}?session_id=` | `rename_task()` |
| DELETE | `/api/v1/tasks/{id}?session_id=` | `delete_task()` |
| POST | `/api/v1/tasks/{id}/activate?session_id=` | `activate_task()` |
| POST | `/api/v1/tasks/{id}/inputs?session_id=` | `submit_input(parameter, value, unit)` |
| POST | `/api/v1/tasks/{id}/inputs/{param}/edit?session_id=` | `begin_parameter_edit()` |
| GET | `/api/v1/tasks/{id}/inputs/{param}/edit-impact?session_id=` | `preview_parameter_edit()` |
| GET | `/api/v1/tasks/{id}/workflow-state?session_id=` | `get_workflow_state()` |
| GET | `/api/v1/tasks/{id}/continuation-suggestions?session_id=` | `get_task_continuation_suggestions()` |

### Reports

| Method | Path | Method |
|--------|------|--------|
| GET | `/api/v1/tasks/{id}/reports?session_id=` | `get_task_report()` |
| POST | `/api/v1/tasks/{id}/reports?session_id=` | `generate_task_report(format, with_ai, draft)` |
| GET | `/api/v1/tasks/{id}/reports/preview?format=&session_id=` | `preview_task_report()` |
| GET | `/api/v1/tasks/{id}/reports/download?format=&session_id=` | `download_task_report()` (file attachment) |

### Chat

| Method | Path | Method |
|--------|------|--------|
| GET | `/api/v1/chat/messages?session_id=&task_id=` | `list_chat_messages()` |
| POST | `/api/v1/chat/messages?session_id=` | `post_chat_message(message, task_id, mode, …)` |
| DELETE | `/api/v1/chat/messages?session_id=&task_id=` | `clear_chat_messages()` |

### Materials

| Method | Path | Method |
|--------|------|--------|
| GET | `/api/v1/materials/search?q=` | `search_materials()` |
| GET | `/api/v1/materials/warm` | `warm_material_catalog()` |
| GET | `/api/v1/materials/{material_id}` | `get_material_detail()` |

### Standards (read-only browse)

| Method | Path | Method |
|--------|------|--------|
| GET | `/api/v1/standards/browse?standard=` | `get_standards_browse()` |
| GET | `/api/v1/standards/nodes/{node_id}` | `get_standards_node()` |
| GET | `/api/v1/standards/nodes/{node_id}/subsections/{subsection_id}` | `get_standards_node_subsection()` |
| GET | `/api/v1/standards/tables/{table_id}` | `get_standards_table()` |

### Developer Inspection (gated)

Requires `DEV_INSPECTION_ENABLED=1` (see `engine/inspection/dev_guard.py`). Returns **404** when disabled.

| Method | Path | Method |
|--------|------|--------|
| GET | `/api/v1/tasks/{id}/inspection?session_id=` | `get_inspection()` |
| POST | `/api/v1/tasks/{id}/inspection/breakpoint?session_id=` | `set_inspection_breakpoint(paused, step)` |
| GET | `/api/v1/tasks/{id}/inspection/integrity?session_id=` | `run_inspection_integrity()` |

Note: `integrity` route ignores `task_id` in the URL; it runs pack-wide checks via `run_integrity(reader)`.

---

## `DesktopApiService` wiring

`DesktopApiService` (`desktop_service.py`) is the **single service façade** for all non-dev routes.

### Construction

```text
DesktopApiService.from_project_root(project_root)
  → CLIConfig.load(project_root)
  → migrate_legacy_sessions
  → warm_astm_material_catalog(standards_root)
  → cached StandardsReader via standards_reader_for_config
```

### Delegation map

| Service method | Primary module(s) |
|----------------|-------------------|
| `list_workflows` | `serializers.workflow_catalog` |
| `get_graph_neighbors` | `engine.graph.graph_engine.GraphEngine` |
| Project CRUD | `storage.project_repository`, `ProjectSessionStore` |
| `get_task`, `create_task`, `activate_task`, `submit_input`, … | `workflow_bootstrap`, `parameter_definitions`, `serializers.task_state` |
| `get_workflow_state` | `serializers.workflow_state_payload` (lazy import) |
| `get_inspection`, breakpoints, integrity | `api.inspection` (lazy) |
| Chat | `api.chat_service` |
| Reports | `api.report_service` |
| Materials | `api.material_catalog`, `api.material_detail` |
| Standards browse/nodes/tables | `api.standards_browse`, `api.node_context`, `api.table_context` |
| Continuation | `api.task_continuation_service` |
| Parameter edit | `api.parameter_edit` |

### `task_state` assembly chain

The largest response payload is built by `serializers.task_state`, which composes:

```text
task_state(task, manager, standards_root, reader, projection_mode="interactive")
  → build_parameter_definitions
  → build_display_outputs (output_blocks)
  → build_node_calculation_summaries
  → active_node_context_for_task (node_context)
  → step_provenance (node_provenance)
  → workflow timeline fields (workflow_timeline)
  → equation display helpers (equation_inputs_display)
  → build_flow_guidance_payload (flow_guidance) — Flow Guidance Layer §21
```

**Projection modes:** `interactive` (default for `submit_input`, `get_task`, `activate_task`) omits `engineering_plan`, `engineering_plan_view`, `legacy_goal_map`, `canonical`, and `inspector_summary`. Full planner debug payloads remain on `GET /api/v1/tasks/{id}/inspection` via `build_inspection_payload`. Pass `projection_mode="full"` to `task_state()` for tests or legacy consumers.

**Planning refresh gating:** `refresh_task_planning(..., allow_lightweight_refresh=True)` compares graph-derived structural fields in `planning_structure_signature` (`engine/planner/planning_structure.py`). When structure is unchanged, `goal_tree_refresh` is skipped and `planning_refresh_skipped` is traced. Any snapshot uncertainty or structural delta falls back to full refresh.

### Session model

`session_id` query parameter = **project id**. `ProjectSessionStore` loads `TaskStateManager` from SQLite + per-project filesystem under `config.sessions_dir`.

### Error type

`ApiError(code, message, status=400, details)` — caught in `ApiHandler` and serialized with recovery guidance.

---

## Developer Inspection

| File | Role |
|------|------|
| `inspection.py` | API helpers: `get_inspection_payload`, `set_breakpoint`, `run_integrity`, `persist_replay_snapshot` |
| `engine/inspection/*` | Payload building, trace, replay frames, integrity checks |
| `engine/inspection/dev_guard.py` | `inspection_enabled()` reads `DEV_INSPECTION_ENABLED` |

**Enable:** `DEV_INSPECTION_ENABLED=1` on backend. Unpackaged Electron sets this automatically (`backendProcess.ts`).

**Desktop client:** `desktopApp/src/services/api/inspectionApi.ts` → Inspector UI (`DeveloperInspector.tsx`).

**Executor hook:** `engine/executor/executor.py` calls `persist_replay_snapshot` after steps when inspection is enabled.

---

## Execution Traces

### Desktop: create task and submit input

```text
User: New task (desktopApp taskApi.post)
  → POST /api/v1/tasks?session_id=
  → server.do_POST → DesktopApiService.create_task
  → Router.supported_workflows check
  → bootstrap_new_task (workflow_bootstrap)
  → serializers.task_state → JSON

User: Submit parameter (inputApi.post)
  → POST /api/v1/tasks/{id}/inputs
  → submit_task_input (parameter_definitions)
      → engine resolvers (NPS, allowable stress, coefficients, …)
  → refresh_task_planning → maybe_execute_ready_workflow
  → try_complete_definition_equations (if execution trace exists)
  → serializers.task_state
```

### Desktop: generate report

```text
reportApi.post → generate_task_report (report_service)
  → engine.reports.ReportGenerator
  → files under session reports/
```

### Inspection: fetch panel data

```text
inspectionApi.get → get_inspection (inspection.py)
  → require_inspection_enabled
  → engine.inspection.builder.build_inspection_payload
```

### Flow Guidance: task state field

```text
GET /api/v1/tasks/{id} → serializers.task_state
  → build_flow_guidance_payload (flow_guidance.py)
  → GuidanceResolver + ResponseComposer
  → JSON: flow_guidance.presentation_blocks, transcript_blocks, active_prompt
```

Evidence: `tests/api/test_guidance_blocks.py`.

---

## Duplicate Implementations

| Area | Instances | Notes |
|------|-----------|-------|
| Health endpoint | `server.py` `/health` and `health_server.py` | Two standalone servers can serve `/health`; only `api.server` is used by Electron |
| Material search naming | `material_catalog.search_astm_materials` vs `search_material_catalog` | Alias wrappers over `material_catalog_service` |
| Workflow catalog | `serializers.WORKFLOW_CATALOG` static tuple vs `GraphEngine.list_workflows` dynamic | `workflow_catalog(reader)` merges both |
| Standards reader construction | `DesktopApiService._reader()` vs `standards_reader_for_config` in some methods | `get_standards_*` methods call `standards_reader_for_config` directly instead of cached `_reader()` |

---

## Possible Dead Code

| Symbol / file | Why it appears unused | Confidence |
|---------------|----------------------|------------|
| `health_server.py` | No importers; Electron uses `api.server` which includes `/health` | **High** |
| `desktop_service._session_updated_at` | Defined, never called | **High** |
| `serializers.workflow_catalog_legacy` | Defined, no importers | **High** |
| `GET /api/v1/graph/neighbors` | No `desktopApp` client; no `dev/` usage found | **Medium** — may be manual/API consumer |
| `GET /api/v1/tasks/{id}/workflow-state` | Tested in `tests/api/test_workflow_state_api.py`; documented in `graph_platform.md`; no desktop client | **Medium** |
| `node_repository._DEFAULT_TYPE_PATHS`, `_KIND_PATHS` | Defined in `node_repository.py`, `_default_rel_path` returns `nodes/{node_id}` only | **Medium** — legacy path helpers |

Do not delete without explicit approval.

---

## Notes

- **HTTP stack:** stdlib `HTTPServer` only — no FastAPI/Flask.
- **PUT vs PATCH:** Dev studio node updates use PUT; tasks/projects use PATCH for rename.
- **Pipe wall stale refresh:** `get_task` / `activate_task` call `_maybe_refresh_stale_pipe_wall_task` for legacy tasks missing `t_m`.
- **`table_context.py`:** Duplicate import line `from engine.reference.standards_tables import flatten_lookup_table_rows` (lines 15–16).
- **Inspection integrity URL** includes `task_id` but backend uses session-wide `run_integrity(reader)` only.

---

## Files (summary)

| File | One-line role |
|------|---------------|
| `server.py` | HTTP server, route table, dev studio bootstrap |
| `desktop_service.py` | REST service façade, `ApiError`, session/project/task orchestration |
| `serializers.py` | `task_state`, `task_summary`, `workflow_catalog`, `workflow_state_payload` |
| `json_encoding.py` | `json_safe`, `dumps` for API JSON |
| `error_catalog.py` | User-facing error recovery metadata |
| `workflow_bootstrap.py` | New task bootstrap, planning refresh, workflow execution |
| `workflow_timeline.py` | Revealed inputs, step titles, MAWP/pipe-wall timeline |
| `parameter_definitions.py` | UI parameter specs + `submit_task_input` |
| `parameter_edit.py` | Timeline parameter edit impact / begin edit |
| `output_blocks.py` | Ordered display blocks for center panel |
| `equation_inputs_display.py` | Formula tables, substitution, thickness display |
| `node_display.py` | Activated definition node blocks |
| `node_context.py` | Active node context, standards node source payloads |
| `node_provenance.py` | Provenance tooltips, step provenance enrichment |
| `node_calculation_summaries.py` | Per-node calculation cards from execution trace |
| `standards_browse.py` | Standards tree for left-panel browse |
| `standards_retrieval.py` | RAG-style standards context for chat |
| `table_context.py` | Table source payloads for UI |
| `material_catalog_service.py` | Cached global material catalog DB |
| `material_catalog.py` | Thin search/warm wrappers |
| `material_detail.py` | Material grade detail for reference tab |
| `chat_service.py` | Chat list/send/clear with AI agents |
| `chat_orchestrator.py` | Flow Guidance on `waiting_input` turns; `presentation` + `new_transcript_blocks` in chat data |
| `flow_guidance.py` | `build_flow_guidance_payload` → `task_state["flow_guidance"]` |
| `center_panel_contract.py` | Contract `display_role` mapping; scroll assembly; archives excluded from center-panel merge |
| `completion_next_workflows_transcript.py` | Durable `next_workflows` block on task completion |
| `chat_context.py` | Task context brief, conversation trimming |
| `report_service.py` | Report generate/preview/download/status |
| `task_continuation_service.py` | Post-completion AI suggestions |
| `inspection.py` | Developer inspection API (gated) |
| `health_server.py` | Minimal standalone health server |

---

## Per-file inventory

Confidence: **High** = clear importers and runtime path; **Medium** = indirect or test-only; **Low** = uncertain.

### `server.py`

- **Purpose:** Bind `HTTPServer` to `ApiHandler`; map paths to `DesktopApiService`.
- **Public:** `ApiHandler`, `create_handler`, `main`, `_parse_task_route`
- **Side effects:** Listens on TCP; reads env `BACKEND_HOST`, `BACKEND_PORT`, `PROJECT_ROOT`
- **Imports:** `desktop_service`, `error_catalog`, `json_encoding`
- **Imported by:** `python -m api.server` only (no Python imports)
- **Active:** Yes — **High**

### `desktop_service.py`

- **Purpose:** Application service layer for all desktop REST operations.
- **Public:** `ApiError`, `DesktopApiService`, `from_project_root`
- **Side effects:** SQLite, filesystem (sessions, reports), standards reader cache, shutil on project delete
- **Imports:** `cli.*`, `config`, `engine.*`, `storage.*`, many `api.*` helpers
- **Imported by:** `server.py`, all `tests/api/*` using service, `api.inspection`
- **Active:** Yes — **High**

### `serializers.py`

- **Purpose:** Build `task_state` and related DTOs for the desktop UI.
- **Public:** `task_state`, `task_summary`, `workflow_catalog`, `workflow_state_payload`, `WORKFLOW_CATALOG`
- **Imports:** Most display/timeline modules in `api/`
- **Imported by:** `desktop_service`, `chat_service`, `task_continuation_service`, tests
- **Active:** Yes — **High**

### `json_encoding.py`

- **Purpose:** Recursive JSON serialization for dataclasses, Enums, Path, datetime.
- **Public:** `json_safe`, `dumps`, `json_default`
- **Imported by:** `serializers`, `server`, `engine/inspection/builder`, tests
- **Active:** Yes — **High**

### `error_catalog.py`

- **Purpose:** Attach `recovery` guidance to API error payloads.
- **Public:** `enrich_api_error_payload`, `build_recovery`
- **Imported by:** `server`, `serializers`
- **Active:** Yes — **High**

### `workflow_bootstrap.py`

- **Purpose:** Initialize new tasks; refresh planning; optional workflow execution.
- **Public:** `bootstrap_new_task`, `refresh_task_planning`, `maybe_execute_ready_workflow`, `task_ready_for_execution`, `standards_reader_for_config`, `resolve_activated_definition_node`
- **Imported by:** `desktop_service`, `output_blocks`, `node_context`, `node_provenance`, tests
- **Active:** Yes — **High**

### `workflow_timeline.py`

- **Purpose:** Workflow-specific input ordering and reveal rules (pipe wall, MAWP).
- **Public:** `is_pipe_wall_thickness_task`, `is_mawp_task`, `revealed_*`, `submittable_parameter_ids`, step title helpers
- **Imported by:** `serializers`, `parameter_definitions`, `parameter_edit`, `output_blocks`, `workflow_bootstrap`
- **Active:** Yes — **High**

### `parameter_definitions.py`

- **Purpose:** Build parameter form definitions; validate and apply submitted inputs.
- **Public:** `build_parameter_definitions`, `submit_task_input`
- **Imported by:** `desktop_service`, `serializers`, tests
- **Active:** Yes — **High**

### `parameter_edit.py`

- **Purpose:** Assess downstream impact of editing a timeline parameter; start edit session.
- **Public:** `assess_parameter_edit`, `begin_parameter_edit`, `active_edit_parameter`, `is_timeline_parameter_editable`
- **Imported by:** `desktop_service`, `parameter_definitions`, `serializers`
- **Active:** Yes — **High**

### `output_blocks.py`

- **Purpose:** Workflow-agnostic ordered blocks (equations, tables, paragraphs, results) for the task center panel.
- **Public:** `build_display_outputs`
- **Pipeline:** warnings → focus-filtered activation → path equation preview → paragraph/validation blocks from trace → execution-trace blocks (equations, lookup tables) → result blocks → `_finalize_display_blocks` (provenance, dedupe, `append_equation_trace_blocks`).
- **Stable ids:** `equation-trace-{source_node_id}-{equation_node_id}`, `table-lookup-{node_id}`, `paragraph-{node_id}`, `validation-{semantic_key}` — no workflow-specific builder branches.
- **Schedule lookup:** B36.10 table rows are read from `_execution_trace` (`engine/executor/pipe_schedule_recommendation.py`); display does not query tables at serialize time.
- **Imported by:** `serializers`, `engine/reports/report_data`, `engine/inspection/provenance`, tests
- **Active:** Yes — **High**
- **Companion:** `paragraph_display.py` reads paragraph `presentation.*` metadata for engineering reference blocks.

### `paragraph_display.py`

- **Purpose:** Generic paragraph/text blocks for center panel from node `presentation.*` metadata.
- **Public:** `build_paragraph_display_block`, `paragraph_blocks_from_trace`
- **Imported by:** `output_blocks.py`, tests
- **Active:** Yes — **High**

### `center_panel_contract.py`

- **Purpose:** Shared center-panel / report-preview presentation contract; assembles scroll blocks from transcript + `display_outputs`.
- **Public:** `assemble_center_panel_scroll_blocks`, `presentation_package_from_task_state`, `sort_blocks_by_report_role` (via `models.display_role.resolve_display_block`)
- **Scroll exclusion:** `ask_archive` / `answer_archive` are not mapped into `ordered_scroll_blocks` (composer owns Q&A).
- **Imported by:** `serializers`, tests
- **Active:** Yes — **High**

### `reference_links.py`

- **Purpose:** Read-only reference chip resolution for API/desktop presentation blocks.
- **Public:** `enrich_display_output_dict`, `enrich_row_provenance_dict`, `select_primary_reference_chip`, `resolve_reference_chips`
- **Imported by:** `output_blocks`, `serializers`, tests
- **Active:** Yes — **High**

### `equation_inputs_display.py`

- **Purpose:** Formula input tables and LaTeX substitution strings (legacy pipe-wall migration helpers).
- **Public:** Many `build_*` and `format_*` helpers
- **Imported by:** `output_blocks`, `serializers`, `node_calculation_summaries`, tests
- **Active:** Yes — **High** (migration fallback; new equations use `equation_display_trace`)

### `equation_display_trace_serializer.py`

- **Purpose:** Thin API wrapper over `engine/equation/display_trace_serializer.py`.
- **Public:** `enrich_equation_block`, `find_trace_for_equation`, `trace_to_dict`
- **Imported by:** `equation_evaluation_display.py`, tests
- **Active:** Yes — **High**

### `equation_evaluation_display.py`

- **Purpose:** Graph-driven equation preview/trace blocks; attaches inline `equation_display_trace` when execution or live blocked trace is available.
- **Public:** `build_equation_evaluation_block`, `build_equation_trace_block`
- **Imported by:** `output_blocks.py`, `display_block_metadata.py`, tests
- **Active:** Yes — **High**

### `node_display.py`

- **Purpose:** Display blocks when a definition node is activated at workflow start.
- **Public:** `build_activated_node_blocks`
- **Imported by:** `output_blocks`, tests
- **Active:** Yes — **High**

### `node_context.py`

- **Purpose:** Active node hover context; full node/subsection source for standards panel.
- **Public:** `active_node_context_for_task`, `node_source_payload`, `subsection_source_payload`, `hover_excerpt_for_node`, `display_heading_for_node`
- **Imported by:** `desktop_service`, `serializers`, `node_provenance`, `standards_retrieval`, `table_context`
- **Active:** Yes — **High**

### `node_provenance.py`

- **Purpose:** Compact provenance for parameters and display blocks.
- **Public:** `provenance_for_node`, `enrich_display_blocks_provenance`, `step_provenance`, `param_node_index`
- **Imported by:** `serializers`, `parameter_definitions`, `output_blocks`, `engine/inspection/provenance`
- **Active:** Yes — **High**

### `node_calculation_summaries.py`

- **Purpose:** Right-panel per-node calculation summaries from `_execution_trace`.
- **Public:** `build_node_calculation_summaries`
- **Imported by:** `serializers`, tests
- **Active:** Yes — **High**

### `standards_browse.py`

- **Purpose:** Hierarchical browse tree (workflows, sections, tables).
- **Public:** `build_standards_browse_payload`, `resolve_browse_standard`
- **Imported by:** `desktop_service`, tests
- **Active:** Yes — **High**

### `standards_retrieval.py`

- **Purpose:** Select standards nodes/tables for chat grounding.
- **Public:** `retrieve_standards_context`
- **Imported by:** `chat_service`, tests
- **Active:** Yes — **High**

### `table_context.py`

- **Purpose:** Serialize lookup table data for standards UI.
- **Public:** `table_source_payload`
- **Imported by:** `desktop_service`, `standards_retrieval`, tests
- **Active:** Yes — **High**

### `material_catalog_service.py`

- **Purpose:** Thread-safe cache for `GlobalMaterialCatalog` warm-up and search.
- **Public:** `get_material_catalog`, `warm_material_catalog`, `search_material_catalog`
- **Imported by:** `material_catalog`, `material_detail`, `workflow_bootstrap`, tests
- **Active:** Yes — **High**

### `material_catalog.py`

- **Purpose:** API-facing aliases for material search/warm.
- **Public:** `search_astm_materials`, `warm_astm_material_catalog`
- **Imported by:** `desktop_service`, tests
- **Active:** Yes — **High**

### `material_detail.py`

- **Purpose:** Full material grade payload for reference tab.
- **Public:** `get_material_detail`
- **Imported by:** `desktop_service`, tests
- **Active:** Yes — **High**

### `chat_service.py`

- **Purpose:** Persist and process chat messages; invoke TaskAssist / SelectionExplain agents.
- **Public:** `list_chat_messages`, `send_chat_message`, `clear_chat_messages`, `serialize_message`
- **Imported by:** `desktop_service`, tests
- **Active:** Yes — **High**

### `chat_context.py`

- **Purpose:** Trim history; build textual task brief for LLM prompts.
- **Public:** `build_task_context_brief`, `prior_turns_for_llm`, `trim_conversation_history`
- **Imported by:** `chat_service`, `task_continuation_service`, tests
- **Active:** Yes — **High**

### `report_service.py`

- **Purpose:** Report lifecycle (status, generate, preview, download paths).
- **Public:** `generate_task_report`, `get_report_status`, `get_report_preview`, `resolve_report_download`
- **Imported by:** `desktop_service`, tests
- **Active:** Yes — **High**

### `task_continuation_service.py`

- **Purpose:** AI suggestions after task completion.
- **Public:** `get_continuation_suggestions`
- **Imported by:** `desktop_service`, tests
- **Active:** Yes — **High**

### `inspection.py`

- **Purpose:** Gated inspection REST helpers and executor replay persistence.
- **Public:** `get_inspection_payload`, `set_breakpoint`, `run_integrity`, `persist_replay_snapshot`, `require_inspection_enabled`
- **Imported by:** `desktop_service` (lazy), `engine/executor/executor.py` (lazy)
- **Active:** Yes when `DEV_INSPECTION_ENABLED=1` — **High**

### `health_server.py`

- **Purpose:** Minimal `/health` server for early-phase startup checks.
- **Public:** `HealthHandler`, `main`
- **Imported by:** None found
- **Active:** Only if run directly — **Low**

### `__init__.py`

- **Purpose:** Package docstring.
- **Active:** N/A

---

## Desktop client mapping

| Backend route | TypeScript module |
|---------------|-------------------|
| Projects | `desktopApp/src/services/api/projectApi.ts` |
| Tasks / workflows / recent | `desktopApp/src/services/api/taskApi.ts` |
| Inputs / edit | `desktopApp/src/services/api/inputApi.ts` |
| Chat | `desktopApp/src/services/api/chatApi.ts` |
| Reports | `desktopApp/src/services/api/reportApi.ts` |
| Materials | `desktopApp/src/services/api/materialApi.ts` |
| Standards browse/nodes/tables | `desktopApp/src/services/api/standardsApi.ts` |
| Continuation | `desktopApp/src/services/api/taskContinuationApi.ts` |
| Inspection | `desktopApp/src/services/api/inspectionApi.ts` |
| Health | `desktopApp/src/config/constants.ts` (`buildHealthUrl`) |

**No desktop client found for:** `/api/v1/graph/neighbors`, `/api/v1/tasks/{id}/workflow-state`.

---

## Related docs

- [docs/developer_inspection_framework.md](../docs/developer_inspection_framework.md) — inspection UI
- [docs/audit/PROGRESS.md](../docs/audit/PROGRESS.md) — audit tracker
