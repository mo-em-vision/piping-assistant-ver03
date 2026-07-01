# cli/ — Architecture Audit

Audit date: 2026-07-01. Documentation reflects the code as it exists today; no architectural recommendations.

---

## Purpose

The `cli/` package is the **Typer + Rich command-line interface** for the engineering assistant. It is an **interface layer only**: it collects user input, persists session/task state to disk, formats terminal output, and wires requests through AI agents and the engine. It does **not** own engineering calculations, standards graph logic, or workflow execution.

The same orchestration and session primitives are also imported by the REST API (`api/chat_service.py`, `api/desktop_service.py`) and desktop storage (`storage/project_session_store.py`), so `cli/` is shared infrastructure—not CLI-exclusive code.

---

## Files

| File | Role |
|------|------|
| `__init__.py` | Re-exports `app` from `cli.app`. |
| `__main__.py` | Module entry: `python -m cli` invokes `app()`. |
| `app.py` | Typer application root; global `--debug-ai`; registers subcommands. |
| `orchestrator.py` | `ChatOrchestrator` — wires agents, input extraction, and state manager for chat. |
| `session_store.py` | Filesystem session persistence under `sessions/<session_id>/`. |
| `responses.py` | `CLIResponse` dataclass for structured assistant replies. |
| `display.py` | Rich terminal formatting helpers. |
| `standards_reader.py` | Backward-compatible re-export of `engine.reference.standards_reader`. |
| `commands/chat.py` | Interactive `chat` command loop. |
| `commands/tasks.py` | `task list`, `task resume`, `task trace`. |
| `commands/reports.py` | `report generate` (PDF/HTML/Markdown/JSON). |
| `commands/graph.py` | `graph show` — dependency tree from standards packs. |
| `commands/nodes.py` | `node inspect`, `node validate`. |

There is no `cli/commands/__init__.py` in the repository.

---

## Entry Points

| Entry | How it is reached |
|-------|-------------------|
| `main.py` (repo root) | `from cli.app import app` → `app()` when `__name__ == "__main__"`. |
| `python -m cli` | `cli/__main__.py` imports and calls `app()`. |
| `from cli import app` | `cli/__init__.py` re-export. |
| `cli.app.app` | Imported directly by tests (`tests/cli/test_app.py`, `tests/mvp/test_security.py`, `tests/acceptance/test_interface.py`). |

Individual modules (`orchestrator.py`, `session_store.py`, etc.) are **library entry points** imported by CLI commands, API services, and tests—not run as scripts.

The Typer app is named `piping-assistant` (`cli/app.py` line 17), but there is **no** `console_scripts` / setuptools entry point in the repo. Invocation is via `python main.py` or `python -m cli`.

---

## Dependencies

### This folder depends on

| Area | Modules used by `cli/` |
|------|------------------------|
| **CLI framework** | `typer`, `rich` (Console, Panel, Markdown, Table, Tree, Prompt) |
| **Config** | `config.loader.CLIConfig` |
| **AI layer** | `ai.agents.*` (ContextAgent, IntentAgent, PlannerAgent, InputAgent), `ai.client`, `ai.input_extractor`, `ai.interaction_specs`, `ai.response.response_handler` |
| **Engine** | `engine.router` (constant only in orchestrator), `engine.state.state_manager`, `engine.reference.standards_reader`, `engine.graph.*`, `engine.messaging.*`, `engine.reports.report_generator` |
| **Models** | `models.agent`, `models.input`, `models.planning`, `models.task` |
| **Stdlib** | `json`, `pathlib`, `dataclasses`, `datetime`, `uuid`, `typing`, `collections.abc` |

### Who depends on this folder

Grep for `from cli.` / `import cli` across the repo (2026-07-01):

| Consumer | Imports |
|----------|---------|
| `main.py` | `cli.app.app` |
| `api/chat_service.py` | `ChatOrchestrator`, `CLIResponse`, `SessionStore` |
| `api/task_continuation_service.py` | `SessionStore` |
| `api/desktop_service.py` | `new_task_id`, `_task_from_dict` |
| `storage/project_session_store.py` | `_input_from_dict`, `_input_to_dict`, `_task_from_dict`, `_task_to_dict` |
| `tests/cli/*` | `app`, `ChatOrchestrator`, `SessionStore`, `StandardsReader`, `resolve_incomplete_task_choice` |
| `tests/api/test_chat_api.py`, `test_rename.py` | `SessionStore`, serialization helpers |
| `tests/acceptance/*`, `tests/mvp/*` | `app`, `ChatOrchestrator`, `SessionStore` |

Docs referencing `cli/` (not runtime imports): `docs/core/9. cli_design.md`, `docs/core/1. Architecture.md`, `docs/core/12. Cursor Build Sequence.md`, root `README.md`.

---

## Runtime Usage

**Yes — `cli/` is on the live execution path** for terminal use and is partially reused by the desktop REST API.

### Proof (executed 2026-07-01)

```text
> python main.py --help
Commands: chat, task, report, graph, node

> python -m cli --help
(same command tree)

> python main.py task --help
Subcommands: list, resume, trace

> python main.py graph show pipe_wall_thickness_design
B313-PIPE-WALL-THICKNESS-DESIGN (root) …

> python main.py task list
(table of tasks in sessions/default/)

> python -m pytest tests/cli/test_app.py -q
5 passed
```

### Typical CLI startup flow

```text
python main.py [global options] <command>
    ↓
cli/app.py — module import runs build_app()
    ↓
get_config() → CLIConfig.load()
    ↓
register_task_commands / register_report_commands / register_graph_commands / register_node_commands
    ↓
Typer dispatches command handler
```

### Chat command flow (primary orchestration path)

```text
chat command (cli/app.py)
    ↓
cli/commands/chat.py — run_chat()
    ↓
SessionStore.load_state_manager() → TaskStateManager
    ↓
ChatOrchestrator.handle_message()
    ↓
agents (Context → Intent → Planner → Input) + engine modules
    ↓
CLIResponse → display helpers → SessionStore.save_state_manager()
```

---

## Possible Dead Code

| Item | Why it appears unused | Confidence |
|------|----------------------|------------|
| `SessionStore.list_sessions()` | No callers in repo (`grep` for `SessionStore.list_sessions` / `store.list_sessions` — zero hits). `ProjectSessionStore` has its own `list_sessions` used by desktop storage. | **High** |
| `Optional` import in `cli/app.py` | Imported from `typing` but never referenced in the file. | **High** |
| `cli/standards_reader.py` as a distinct module | Thin re-export; `cli/orchestrator.py` imports `StandardsReader` directly from `engine.reference.standards_reader`, bypassing the shim. Only `commands/graph.py` and `commands/nodes.py` use `cli.standards_reader`. | **Medium** — shim is used, but duplicate import paths exist |
| `CLIResponse.to_dict()` within `cli/` | Not called by any `cli/` module; used by `api/chat_service.py` for JSON responses. | **Low** — dead **inside CLI**, active via API |
| `build_app()` return value | Return value of `build_app()` is discarded at module level (`build_app()`); side effect (registering commands) is the purpose. | **Low** — not dead; return value unused |

Nothing in this folder should be deleted based on this audit alone.

---

## Notes

### Duplicate / parallel implementations

| Topic | Observation |
|-------|-------------|
| **StandardsReader** | `cli/standards_reader.py` re-exports `engine.reference.standards_reader`. `orchestrator.py` imports from `engine` directly; graph/node commands import via `cli.standards_reader`. Same class, two import paths. |
| **Task serialization** | `_task_to_dict`, `_task_from_dict`, `_input_to_dict`, `_input_from_dict` in `session_store.py` are imported by `storage/project_session_store.py` for SQLite-backed desktop sessions. Shared serialization, not duplicated logic. |
| **ChatOrchestrator** | Used by both `cli/commands/chat.py` and `api/chat_service.py`. Single implementation, two hosts. |
| **SessionStore vs ProjectSessionStore** | CLI uses filesystem `SessionStore`; desktop API uses `ProjectSessionStore` (wraps DB + reuses serialization helpers). Parallel persistence layers. |

### Documentation drift

Root `README.md` lists `python main.py task show <task_id>` and `python main.py node show …`. The implemented commands are `task trace` and `node inspect` / `node validate` (verified via `python main.py --help` and `tests/cli/test_app.py`).

Docs refer to `piping-assistant` as the command name; actual invocation is `python main.py` or `python -m cli`.

### Unusual patterns

- `build_app()` runs at **import time** (bottom of `cli/app.py`), so subcommands are registered when the module loads, not lazily on first `app()` call.
- `_debug_ai` is a module-level global set by the Typer callback; only the `chat` command reads it.
- `task resume` hard-codes pipe-wall-thickness input keys (`design_pressure`, `outside_diameter`, `allowable_stress`) for status display — not generic across workflows.

---

## Execution trace: `main.py` → `engine/router.py`

There are **two** connections from the CLI stack to `engine/router.py`. The orchestrator does **not** call `route()` directly; routing goes through `IntentAgent`.

### Path A — Chat command (terminal)

```text
main.py
  app()                                    # cli/app.py
    chat()                                 # @app.command("chat")
      run_chat(get_config(), debug_ai=…)   # cli/commands/chat.py
        ChatOrchestrator(manager)          # cli/orchestrator.py
          handle_message(user_message)
            [active task branch]
              intent_agent.analyze(…)      # ai/agents/intent_agent.py
                route(request)             # engine/router.py  ← keyword classification
              planner_agent.plan_navigation(…)
            context_agent.evaluate(…)
            intent_agent.analyze(…)          # second pass
              route(request)                 # engine/router.py  (if no active workflow context)
            planner_agent.plan_navigation(…)
            input_agent.analyze(…)
            _resolve_workflow(active)
              return PIPE_WALL_THICKNESS_DESIGN   # engine/router.py constant import
```

### Path B — API chat (desktop; reuses cli orchestrator)

```text
api/server.py → api/chat_service.py
  ChatOrchestrator(state_manager, …)
    handle_message(…)
      IntentAgent.analyze → engine.router.route()
```

### What `engine/router.py` provides to this path

| Symbol | Used where | Role |
|--------|------------|------|
| `route(request)` | `ai/agents/intent_agent.py` (called from `ChatOrchestrator`) | Deterministic keyword → workflow name |
| `PIPE_WALL_THICKNESS_DESIGN` | `cli/orchestrator.py` `_resolve_workflow()` | Default workflow when task outputs lack `workflow` key |
| `Router` class, `MAWP_DESIGN` | Not imported by any `cli/` file | Used elsewhere (`api/desktop_service.py`, etc.) |

### Other CLI commands (no `engine/router.py` on path)

| Command | Trace terminus |
|---------|----------------|
| `task list/resume/trace` | `SessionStore` + `TaskStateManager` |
| `report generate` | `ReportGenerator` (`engine/reports/`) |
| `graph show` | `StandardsReader.dependency_tree()` |
| `node inspect/validate` | `StandardsReader.load()` / `.validate()` |

---

## Per-file inventory

### `cli/__init__.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Package marker; exposes `app` for `from cli import app`. |
| **Public API** | `app`, `__all__ = ["app"]` |
| **Inputs** | None (import side effects: loads `cli.app` which runs `build_app()`). |
| **Outputs** | `app` Typer instance. |
| **Side effects** | Registers all Typer subcommands via `cli.app` import. |
| **Importers** | Unknown from static analysis as a direct `import cli` consumer (typically `from cli import app` or `python -m cli`). |
| **Imports** | `cli.app.app` |
| **Active use** | Yes |
| **Confidence** | High |

---

### `cli/__main__.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Module execution entry for `python -m cli`. |
| **Public API** | None (script-style). |
| **Inputs** | `sys.argv` via Typer. |
| **Outputs** | Process exit code from Typer. |
| **Side effects** | Runs CLI; may read/write `sessions/`. |
| **Importers** | Python `-m cli` loader only. |
| **Imports** | `cli.app.app` |
| **Active use** | Yes |
| **Confidence** | High |

---

### `cli/app.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Root Typer application and command registration. |
| **Public API** | `app`, `get_config()`, `build_app()`, `main()` callback, `chat()` command. |
| **Inputs** | CLI args; `--debug-ai` global flag. |
| **Outputs** | Typer dispatch; `chat` invokes `run_chat`. |
| **Side effects** | `build_app()` at import registers `task`, `report`, `graph`, `node` command groups; `_config` lazy-loaded. |
| **Importers** | `main.py`, `cli/__init__.py`, `cli/__main__.py`, `tests/cli/test_app.py`, `tests/mvp/test_security.py`, `tests/acceptance/test_interface.py` |
| **Imports** | `typer`; `cli.commands.*`; `config.loader.CLIConfig` |
| **Active use** | Yes |
| **Confidence** | High |

---

### `cli/orchestrator.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Coordinate agents and state for conversational engineering requests. |
| **Public API** | `ChatOrchestrator`, `handle_message()`, private helpers (`_resolve_workflow`, `_extract_and_store_inputs`, etc.). |
| **Inputs** | `message: str`, `debug_ai: bool`; constructor takes `TaskStateManager`, optional `llm_client`, `standards_root`. |
| **Outputs** | `tuple[CLIResponse, dict[str, Any]]` (response + optional debug payload). |
| **Side effects** | Creates/updates tasks and inputs via `TaskStateManager`; may call OpenAI if API key present. |
| **Importers** | `cli/commands/chat.py`, `api/chat_service.py`, tests (`tests/cli/test_orchestrator.py`, `tests/acceptance/*`, `tests/mvp/*`) |
| **Imports** | `ai.agents.*`, `ai.client`, `ai.input_extractor`, `ai.interaction_specs`, `ai.response.response_handler`; `engine.router.PIPE_WALL_THICKNESS_DESIGN`; `engine.reference.standards_reader`, `engine.state.state_manager`, `engine.graph.*`, `engine.messaging.*`; `models.*`; `cli.responses`, `cli.session_store` |
| **Active use** | Yes — core chat path for CLI and API |
| **Confidence** | High |

---

### `cli/session_store.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Persist tasks and conversation JSON under `sessions/<session_id>/`. |
| **Public API** | `SessionStore`, `new_task_id()`, module-level `_task_to_dict`, `_task_from_dict`, `_input_to_dict`, `_input_from_dict`, `_json_default`. |
| **Inputs** | `sessions_dir: Path`, optional `session_id`; task/manager state for save/load. |
| **Outputs** | `TaskStateManager`, conversation message lists, written JSON files. |
| **Side effects** | Creates `sessions/<id>/`, `tasks.json`, `conversation.json`, `reports/` subdirectory. |
| **Importers** | `cli/commands/*`, `api/chat_service.py`, `api/task_continuation_service.py`, `api/desktop_service.py` (partial), `storage/project_session_store.py` (serialization helpers), many tests |
| **Imports** | `engine.state.state_manager`; `models.input`, `models.task`; stdlib `json`, `pathlib`, `uuid`, etc. |
| **Active use** | Yes |
| **Confidence** | High |

---

### `cli/responses.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Structured response object for chat and API serialization. |
| **Public API** | `CLIResponse` dataclass, `to_dict()`. |
| **Inputs** | `status`, optional `message`, `question`, `required_by`, `task_id`, `data`. |
| **Outputs** | `CLIResponse` instance; `to_dict()` → `dict`. |
| **Side effects** | None |
| **Importers** | `cli/orchestrator.py`, `cli/display.py`, `api/chat_service.py` |
| **Imports** | stdlib `dataclasses`, `typing` |
| **Active use** | Yes |
| **Confidence** | High |

---

### `cli/display.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Rich-based terminal output. |
| **Public API** | `console`, `print_banner`, `print_assistant`, `print_error`, `print_debug_block`, `print_cli_response`, `print_task_table`. |
| **Inputs** | Strings, `CLIResponse`, `list[Task]`, debug payloads. |
| **Outputs** | Printed terminal UI (stdout). |
| **Side effects** | Terminal rendering only. |
| **Importers** | `cli/commands/chat.py`, `tasks.py`, `reports.py`, `graph.py`, `nodes.py` |
| **Imports** | `rich.*`; `cli.responses.CLIResponse`; `models.task.Task` |
| **Active use** | Yes |
| **Confidence** | High |

---

### `cli/standards_reader.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Backward-compatible re-export of engine standards reader types. |
| **Public API** | `NodeRecord`, `NodeSubsection`, `NodeValidationResult`, `StandardsReader`, `ValidationIssue` (all from engine). |
| **Inputs** | N/A (re-export). |
| **Outputs** | Re-exported symbols. |
| **Side effects** | None |
| **Importers** | `cli/commands/graph.py`, `cli/commands/nodes.py`, `tests/cli/test_standards_reader.py` |
| **Imports** | `engine.reference.standards_reader` |
| **Active use** | Yes (via graph/node commands); orchestrator bypasses this shim |
| **Confidence** | High |

---

### `cli/commands/chat.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Interactive REPL-style chat session. |
| **Public API** | `run_chat()`, `resolve_incomplete_task_choice()`. |
| **Inputs** | `CLIConfig`, `debug_ai: bool`; user stdin via Rich `Prompt`. |
| **Outputs** | Terminal messages; persisted session state. |
| **Side effects** | Reads/writes `sessions/`; loops until `exit`/`quit`/`:q`. |
| **Importers** | `cli/app.py`, `tests/cli/test_chat_startup.py` |
| **Imports** | `typer`, `rich.prompt`; `cli.display`, `cli.orchestrator`, `cli.session_store`; `config.loader`; `engine.state.state_manager`; `models.task` |
| **Active use** | Yes |
| **Confidence** | High |

---

### `cli/commands/tasks.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Task listing, resume, and trace commands. |
| **Public API** | `register_task_commands(app, config)`. |
| **Inputs** | Typer args (`task_id` for resume/trace); `CLIConfig.sessions_dir`. |
| **Outputs** | Formatted tables/text; exit code 1 on missing task. |
| **Side effects** | Reads/writes `tasks.json` via `SessionStore`. |
| **Importers** | `cli/app.py`, `tests/acceptance/test_interface.py` (monkeypatch) |
| **Imports** | `typer`; `cli.display`, `cli.session_store`; `config.loader`; `engine.state.state_manager` |
| **Active use** | Yes |
| **Confidence** | High |

---

### `cli/commands/reports.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Generate engineering reports for a task. |
| **Public API** | `register_report_commands(app, config)`. |
| **Inputs** | `task_id`, `--format`, `--with-ai`, `--draft`. |
| **Outputs** | Report files under `sessions/<id>/reports/`; assistant message with paths. |
| **Side effects** | File writes via `ReportGenerator`. |
| **Importers** | `cli/app.py`, `tests/acceptance/test_interface.py` (monkeypatch) |
| **Imports** | `typer`; `cli.display`, `cli.session_store`; `config.loader`; `engine.reports.report_generator`; `engine.state.state_manager` |
| **Active use** | Yes |
| **Confidence** | High |

---

### `cli/commands/graph.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Display standards dependency tree. |
| **Public API** | `register_graph_commands(app, config)`; private `_build_rich_tree`, `_standard_slug`. |
| **Inputs** | `node_id` argument; `CLIConfig`. |
| **Outputs** | Rich `Tree` printed to console. |
| **Side effects** | Read-only standards file access. |
| **Importers** | `cli/app.py` |
| **Imports** | `typer`, `rich.tree`; `cli.display`, `cli.standards_reader`; `config.loader` |
| **Active use** | Yes — verified by `tests/cli/test_app.py::test_graph_show_root` |
| **Confidence** | High |

---

### `cli/commands/nodes.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Inspect and validate individual standards nodes. |
| **Public API** | `register_node_commands(app, config)`. |
| **Inputs** | `node_id` argument. |
| **Outputs** | Rich tables; validation PASS/FAIL; exit code 1 on validation failure. |
| **Side effects** | Read-only standards file access. |
| **Importers** | `cli/app.py` |
| **Imports** | `typer`, `rich.table`; `cli.display`, `cli.standards_reader`; `config.loader` |
| **Active use** | Yes — verified by `tests/cli/test_app.py` |
| **Confidence** | High |

---

## Command reference (implemented)

| Command | Handler |
|---------|---------|
| `chat` | `cli/app.py` → `cli/commands/chat.py` |
| `task list` | `cli/commands/tasks.py` |
| `task resume <task_id>` | `cli/commands/tasks.py` |
| `task trace <task_id>` | `cli/commands/tasks.py` |
| `report generate <task_id> [--format] [--with-ai] [--draft]` | `cli/commands/reports.py` |
| `graph show <node_id>` | `cli/commands/graph.py` |
| `node inspect <node_id>` | `cli/commands/nodes.py` |
| `node validate <node_id>` | `cli/commands/nodes.py` |
| `--debug-ai` (global) | `cli/app.py` → passed to `run_chat` only |
