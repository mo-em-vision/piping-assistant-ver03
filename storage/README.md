# storage/ — Architecture Audit

Audited: 2026-07-01. Static analysis only; no code changes.

## Purpose

`storage/` implements **desktop project persistence**: SQLite schema/connections, CRUD for projects/tasks/chat/artifacts, one-time migration from legacy filesystem sessions, and a **session-compatible store** (`ProjectSessionStore`) that mirrors `cli/session_store.SessionStore` while writing to both SQLite and the existing `sessions/` directory layout.

Graph cache databases (`*_graph.db` under standards) live outside this package — see `engine/` / `scripts/build_graph_db.py`.

## Files

| File | Role |
| --- | --- |
| `__init__.py` | Re-exports `DesktopDatabase`, `ProjectRepository`, `ProjectSessionStore`, helpers |
| `desktop_database.py` | SQLite connection, schema init, app metadata key/value |
| `project_repository.py` | SQL CRUD for projects, tasks, chat, artifacts |
| `project_session_store.py` | SessionStore-compatible facade; bridges SQLite ↔ filesystem |
| `migrate_legacy_sessions.py` | One-shot import from legacy `sessions/<id>/` JSON files |

## Entry Points

| Entry | Runnable? | Notes |
| --- | --- | --- |
| `migrate_legacy_sessions()` | Callable only | Invoked from `ProjectSessionStore.__init__` and `DesktopApiService._ensure_storage()` |
| `open_project_store()` | Callable only | **No importers found** outside defining file |
| `get_database_for_config()` | Callable | Used by `api/desktop_service.py`, dev graph explorer |
| `list_project_summaries()` | Callable | Used by `api/desktop_service.py` |
| `ProjectSessionStore` | Instantiated | Primary runtime entry for desktop API |
| `ProjectRepository` | Instantiated | Used directly in API and migration |
| `DesktopDatabase` | Instantiated | Created on first access to desktop DB path |

No `if __name__ == "__main__"` blocks in this package.

## Dependencies

### Internal (within `storage/`)

```
__init__.py              → desktop_database, project_repository, project_session_store
project_repository.py    → desktop_database
project_session_store.py → desktop_database, migrate_legacy_sessions, project_repository
migrate_legacy_sessions.py → desktop_database, project_repository
```

### External (folders/files this package imports)

| Dependency | Used by | Purpose |
| --- | --- | --- |
| `cli/session_store.py` | `project_session_store.py` | `_task_from_dict`, `_task_to_dict`, `_input_from_dict`, `_input_to_dict` — shared serialization with CLI |
| `engine/state/state_manager.py` | `project_session_store.py` | `TaskStateManager`, `TaskAlreadyExistsError`, `TaskNotFoundError` |
| `models/task.py` | `project_session_store.py` | `Task`, `TaskStatus` (type hints / incomplete task filter) |
| Python stdlib | All | `sqlite3`, `json`, `pathlib`, `dataclasses`, `uuid`, `datetime` |

### Dependents (who imports `storage/`)

Grep (`from storage.`):

| Consumer | Imports |
| --- | --- |
| `api/desktop_service.py` | `migrate_legacy_sessions`, `ProjectRepository`, `ProjectSessionStore`, `get_database_for_config`, `list_project_summaries` |
| `api/report_service.py` | `ProjectSessionStore` |
| `dev/graph_explorer/adapter.py` | `migrate_legacy_sessions`, `ProjectRepository`, `ProjectSessionStore`, `get_database_for_config` |
| `dev/graph_explorer/explorer_config.py` | `ProjectRepository`, `get_database_for_config` |
| `tests/storage/test_desktop_database.py` | All main modules |
| `tests/api/test_recent_tasks.py` | `ProjectSessionStore` |

**No** `from storage import …` usage found; consumers import submodule paths.

## Runtime Usage

**Yes — on the desktop application execution path.**

Evidence:

1. `api/desktop_service.py` (served by `api/server.py`) constructs `ProjectSessionStore` for every project-scoped operation (`_store()`, `_store_for()`).
2. DB path: `{project_root}/data/desktop.db` via `get_database_for_config(sessions_dir)` where `sessions_dir` comes from `CLIConfig`.
3. `ProjectSessionStore.__init__` always runs `migrate_legacy_sessions()` before use.
4. Task save/load round-trips through SQLite **and** writes mirror files `sessions/<project_id>/tasks.json` and `conversation.json`.

CLI commands (`cli/commands/chat.py`, `tasks.py`, `reports.py`) use **`cli/session_store.SessionStore` only** (filesystem) — not this package — unless routed through the desktop API.

## Possible Dead Code

| Symbol / file | Why it appears unused | Confidence |
| --- | --- | --- |
| `open_project_store()` in `project_session_store.py` | Grep finds **definition only**; `desktop_service.py` inlines same logic via `_store_for()` + `get_database_for_config()`. | **High** |
| `storage/__init__.py` package re-exports | No `from storage import …` importers. | **Medium** (unused convenience surface) |
| `ProjectSessionStore.list_sessions()` | Defined; desktop API uses `list_project_summaries()` / `ProjectRepository.list_projects()` instead. May be used by unknown dynamic callers. | **Medium** |
| `ProjectSessionStore.append_message()` | Defined on store; grep shows **no callers** outside `project_session_store.py`. Chat flow uses `save_conversation` via repository. | **Medium** |
| `ProjectRepository.load_tasks_payload` `saved_at` | Always set to `utc_now()` on load, not read from DB. | **Low** (behavior quirk, not dead code) |

Do not delete based on this audit alone.

## Notes

### Dual persistence (duplicate implementation)

Two session stores implement the same conceptual interface:

| Store | Location | Backing |
| --- | --- | --- |
| `SessionStore` | `cli/session_store.py` | Filesystem only (`sessions/<id>/tasks.json`, `conversation.json`) |
| `ProjectSessionStore` | `storage/project_session_store.py` | SQLite **plus** same filesystem paths |

`ProjectSessionStore` **depends on** `cli/session_store` serialization helpers — not duplicated.

`api/chat_service.py` and `api/task_continuation_service.py` type-hint `SessionStore` but receive `ProjectSessionStore` at runtime (structural compatibility: shared method names).

### Schema / migration

- Tables: `projects`, `project_tasks`, `chat_messages`, `task_artifacts`, `app_metadata`.
- `chat_messages.sources_json` added via runtime `ALTER TABLE` if missing (`desktop_database.py`).
- Legacy migration key: `app_metadata.legacy_sessions_migrated = "1"`.
- Migration reads `sessions/<dir>/tasks.json` and `conversation.json` per subdirectory name = `project_id`.

### DB vs filesystem layout

```
{project_root}/
  data/desktop.db          ← SQLite (source of truth for API)
  sessions/
    <project_id>/
      tasks.json           ← mirror written on save_state_manager
      conversation.json    ← mirror written on save/clear conversation
      reports/             ← report files (not in storage/ code except mkdir)
```

### Task artifacts

`ProjectRepository.save_tasks_payload` also upserts `task_artifacts` row with `kind='state'`. `save_task_artifact()` used by `api/report_service.py` for report metadata. Artifact rows are not loaded back into `TaskStateManager` in `load_state_manager()` — only `project_tasks.task_json` is loaded.

### Foreign keys

`PRAGMA foreign_keys = ON` on every connection (`desktop_database.connect`).

---

## Per-file inventory

### `__init__.py`

| | |
| --- | --- |
| **Purpose** | Package public exports |
| **Public** | `DesktopDatabase`, `ProjectRepository`, `ProjectSessionStore`, `get_database_for_config`, `list_project_summaries` |
| **Imported by** | No direct importers (submodules imported instead) |
| **Imports** | `storage.desktop_database`, `storage.project_repository`, `storage.project_session_store` |
| **Actively used** | Re-export surface unused; submodules used |
| **Confidence** | **High** |

### `desktop_database.py`

| | |
| --- | --- |
| **Purpose** | SQLite file lifecycle: create dirs, schema, connections, metadata KV |
| **Public** | `utc_now()`, `DesktopDatabase` with `connect()`, `initialize()`, `metadata_get()`, `metadata_set()` |
| **Inputs** | `db_path: Path` |
| **Outputs** | `sqlite3.Connection`; metadata strings |
| **Side effects** | Creates DB file and parent dirs; runs DDL; may `ALTER TABLE chat_messages` |
| **Imported by** | `project_repository.py`, `project_session_store.py`, `migrate_legacy_sessions.py`, `api/desktop_service.py` (via helpers), tests |
| **Imports** | stdlib only |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `project_repository.py`

| | |
| --- | --- |
| **Purpose** | All SQL operations for desktop projects |
| **Public** | `ProjectRepository` — `list_projects`, `get_project`, `ensure_project`, `create_project`, `delete_project`, `update_project_name`, `touch_project`, `load_tasks_payload`, `save_tasks_payload`, `load_conversation`, `clear_conversation`, `save_conversation`, `save_task_artifact`, `list_recent_tasks` |
| **Private** | `_json_default()` for Enum/dataclass/datetime serialization |
| **Inputs** | `DesktopDatabase` instance; project/task/message dicts |
| **Outputs** | dict/list rows; commits to SQLite |
| **Side effects** | INSERT/UPDATE/DELETE on all tables; cascade delete via FK on project delete |
| **Imported by** | `project_session_store.py`, `migrate_legacy_sessions.py`, `api/desktop_service.py`, `dev/graph_explorer/*`, tests |
| **Imports** | `storage.desktop_database` |
| **Actively used** | **Yes** |
| **Confidence** | **High** |

### `migrate_legacy_sessions.py`

| | |
| --- | --- |
| **Purpose** | Import legacy filesystem session dirs into SQLite once |
| **Public** | `MIGRATION_KEY`, `migrate_legacy_sessions(database, sessions_dir)` |
| **Inputs** | `DesktopDatabase`, `Path` to sessions root |
| **Outputs** | None; sets metadata flag |
| **Side effects** | Creates projects; writes tasks/conversation via repository; sets `legacy_sessions_migrated` |
| **Imported by** | `project_session_store.py`, `api/desktop_service.py`, `dev/graph_explorer/adapter.py`, tests |
| **Imports** | `storage.desktop_database`, `storage.project_repository` |
| **Actively used** | **Yes** (runs at store init / service ensure) |
| **Confidence** | **High** |

### `project_session_store.py`

| | |
| --- | --- |
| **Purpose** | SessionStore-compatible API backed by SQLite + filesystem mirrors |
| **Public** | `ProjectSessionStore`, `open_project_store()`, `list_project_summaries()`, `get_database_for_config()` |
| **Key methods** | `load_state_manager`, `save_state_manager`, `load_conversation`, `save_conversation`, `clear_conversation`, `append_message`, `incomplete_tasks`; classmethod `list_sessions` |
| **Inputs** | `DesktopDatabase`, `sessions_dir`, `session_id` (required) |
| **Outputs** | `TaskStateManager`; message lists; summary dicts |
| **Side effects** | Runs migration; mkdir `sessions/<id>/reports/`; writes JSON mirrors; repository commits |
| **Imported by** | `api/desktop_service.py`, `api/report_service.py`, `dev/graph_explorer/adapter.py`, tests |
| **Imports** | `cli/session_store`, `engine/state/state_manager`, `models/task`, `storage/*` |
| **Actively used** | **Yes**; `open_project_store` **No** |
| **Confidence** | **High** |

---

## Execution traces

### Trace 1 — Desktop API startup / first request

```
api/server.py
    ↓
api/desktop_service.py.DesktopApiService.from_project_root()
    ↓
DesktopApiService._ensure_storage()
    ↓
storage/migrate_legacy_sessions.migrate_legacy_sessions(DesktopDatabase, config.sessions_dir)
    ↓
storage/desktop_database.DesktopDatabase  ({root}/data/desktop.db)
    ↓
storage/project_repository.ProjectRepository.ensure_project / save_*  (if legacy dirs exist)
```

### Trace 2 — Load project task state (typical API call)

```
api/desktop_service.py._load_manager()
    ↓
storage/project_session_store.ProjectSessionStore.load_state_manager()
    ↓
storage/project_repository.ProjectRepository.load_tasks_payload(project_id)
    ↓  (reads project_tasks.task_json rows)
cli/session_store._task_from_dict  →  models/task.Task
    ↓
engine/state/state_manager.TaskStateManager
    ↓
api/serializers.task_state  →  HTTP response
```

### Trace 3 — Save task after workflow step

```
engine/state/state_manager.py  (mutated TaskStateManager)
    ↓
api/desktop_service.py._save_manager()
    ↓
ProjectSessionStore.save_state_manager()
    ↓
cli/session_store._task_to_dict  →  models/task.Task serialized
    ↓
ProjectRepository.save_tasks_payload()
    ├→ DELETE + INSERT project_tasks
    ├→ UPSERT task_artifacts (kind='state')
    └→ UPDATE projects.active_task_id, updated_at
    ↓
Write mirror: sessions/<project_id>/tasks.json
```

### Trace 4 — Chat messages

```
api/desktop_service.py.send_chat_message()
    ↓
api/chat_service.py.send_chat_message(store, …)   [store typed SessionStore; actual ProjectSessionStore]
    ↓
ProjectSessionStore.save_conversation(messages)
    ↓
ProjectRepository.save_conversation()  →  chat_messages table
    ↓
Write mirror: sessions/<project_id>/conversation.json
```

### Trace 5 — Project list / create (SQLite project registry)

```
api/desktop_service.py.list_projects()
    ↓
storage/project_session_store.list_project_summaries(DesktopDatabase)
    ↓
ProjectRepository.list_projects()
    ↓
SELECT projects + task COUNT
```

```
api/desktop_service.py.create_project(name)
    ↓
ProjectRepository.create_project()  →  INSERT projects
    ↓
ProjectSessionStore(session_id=new_project_id)  on first use
```

### Trace 6 — Report artifact persistence

```
api/desktop_service.py.generate_task_report()
    ↓
api/report_service.py
    ↓
engine/reports/report_generator.py  →  files under sessions/<id>/reports/
    ↓
api/report_service._save_report_artifact()
    ↓
ProjectRepository.save_task_artifact(project_id, task_id, kind=…, payload_json=…)
    ↓
task_artifacts table
```

### Trace 7 — Dev Graph Explorer

```
dev/graph_explorer/adapter.py
    ↓
get_database_for_config(sessions_dir)
migrate_legacy_sessions()
ProjectSessionStore(database, sessions_dir, session_id=…)
    ↓
load_state_manager()  →  active task subgraph for visualization
```

### Trace 8 — CLI path (does **not** use `storage/`)

```
cli/commands/chat.py
    ↓
cli/session_store.SessionStore  (filesystem only)
    ↓
sessions/<session_id>/tasks.json
```

Parallel persistence path; data may diverge if both CLI and desktop API touch same session id without going through SQLite.

---

## Duplicate implementations (document only)

| Concern | Implementation A | Implementation B |
| --- | --- | --- |
| Session/task persistence | `cli/session_store.SessionStore` | `storage/project_session_store.ProjectSessionStore` |
| Task (de)serialization | `cli/session_store._task_from_dict/_task_to_dict` | Same functions reused by B |
| Project listing | `SessionStore.list_sessions()` (directory names) | `ProjectRepository.list_projects()` / `list_project_summaries()` |
| JSON default handler | `cli/session_store._json_default` | `project_repository._json_default` / `project_session_store._json_default` (three near-identical copies) |

No recommendation on which to keep.
