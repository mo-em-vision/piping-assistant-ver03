# config/ — Architecture Audit

Audit date: 2026-07-01. Documentation reflects the code as it exists today; no architectural recommendations.

---

## Purpose

Holds **Python backend configuration** for the engineering assistant: static defaults in YAML, environment-variable settings (OpenAI, standards root), and the merged `CLIConfig` object used by the CLI, REST API, and dev tools.

This folder is **not** the Electron desktop app config (`desktopApp/src/config/` is a separate TypeScript layer).

---

## Files

| File | Role |
|------|------|
| `config.yaml` | Default CLI/runtime paths and preferences (report format, language, default standard, sessions dir, standards root). |
| `settings.py` | Loads `.env` files at import time; exposes `Settings` dataclass and module-level `settings` singleton from environment variables. |
| `loader.py` | Merges `config.yaml` with `Settings` and path resolution (including `DESKTOP_USER_DATA`) into frozen `CLIConfig`. |

There is no `config/__init__.py` in the repository; the package is resolved when the project root is on `sys.path`.

---

## Entry Points

| Entry | How it is reached |
|-------|-------------------|
| `settings.py` (module import) | Imported by `config/loader.py` and `ai/client.py`. Side effect: `load_env_files()` runs once at import. |
| `CLIConfig.load()` | Called from `api/desktop_service.py` and tests. |
| `config.yaml` | Read only via `CLIConfig.load()` (default path: sibling of `loader.py`). Not executed directly. |

`config.yaml` and `settings.py` are not meant to be run as scripts.

---

## Dependencies

### This folder depends on

| Dependency | Used by |
|------------|---------|
| `config/settings.py` | `loader.py` |
| `PyYAML` (`yaml`) | `loader.py` |
| `python-dotenv` (optional) | `settings.py` — silently skipped if not installed |
| Repo-root `.env`, `desktopApp/.env` | `settings.load_env_files()` |
| Environment variables | `settings.py`, `loader.py` (see Notes) |

### Who depends on this folder

| Consumer | Import |
|----------|--------|
| `api/desktop_service.py`, `api/workflow_bootstrap.py`, `api/chat_service.py`, `api/task_continuation_service.py` | `CLIConfig` |
| `ai/client.py` | `config.settings.Settings`, `settings` |
| `tests/api/*`, `tests/config/*`, `tests/mvp/conftest.py` | `CLIConfig` and/or `Settings` |
| Docs (`README.md`, `docs/core/*`) | Referenced by path only |

The desktop Electron app does **not** import this package; it passes `DESKTOP_USER_DATA` to the backend child process (`desktopApp/electron/services/backendProcess.ts`).

---

## Runtime Usage

**Yes — this folder is on the live execution path.**

Evidence:

1. **Desktop API startup** — `DesktopApiService.from_project_root()` calls `CLIConfig.load(project_root=root)` (`api/desktop_service.py`).
2. **CLI startup** — removed; desktop uses `api/desktop_service.py`.
3. **AI client** — `ai/client.py` reads `settings` (populated after `load_env_files()` on import).

Typical runtime flow:

```
Electron / CLI / pytest
    ↓
import config.loader  (triggers config.settings import → load_env_files())
    ↓
CLIConfig.load()
    ↓ reads config/config.yaml
    ↓ merges Settings (OPENAI_*, STANDARDS_ROOT)
    ↓ resolves sessions_dir, standards_root (DESKTOP_USER_DATA override)
    ↓
DesktopApiService / Typer commands / GraphEngine via StandardsReader
```

---

## Possible Dead Code

| Item | Why it appears unused | Confidence |
|------|----------------------|------------|
| `Settings.standards_root` field | `CLIConfig.load()` reads `standards_root` from `config.yaml`, not from `Settings.standards_root`. The env var `STANDARDS_ROOT` is loaded into `Settings` but not copied into `CLIConfig`. | **High** — field is set in `Settings.from_env()` but no grep hit reads `settings.standards_root` or `env.standards_root` in `loader.py`. |
| `config.yaml` keys when file missing | `CLIConfig.load()` uses hardcoded defaults if `config.yaml` is absent; file is present in repo. | **Low** — defensive fallback, not dead. |

Nothing in this folder should be deleted based on this audit alone.

---

## Notes

- **Two configuration layers**: `config.yaml` (paths, defaults) vs environment (`OPENAI_*`, `DESKTOP_USER_DATA`, `STANDARDS_ROOT`). Only OpenAI fields flow from `Settings` into `CLIConfig`; path defaults come from YAML unless `DESKTOP_USER_DATA` redirects sessions.
- **`DESKTOP_USER_DATA`**: When set, `sessions_dir` becomes `{DESKTOP_USER_DATA}/sessions` and `standards_root` stays relative to project root if not absolute (`loader.py` lines 47–52).
- **`load_env_files()` at import time**: Importing `config.settings` or `config.loader` loads `.env` before most application code runs. `override=False` — existing env vars are not overwritten.
- **No `__init__.py`**: Package works when repo root is on `PYTHONPATH` / `sys.path` (standard for this project).
- **Duplicate config concept**: `desktopApp/src/config/` (frontend env/constants) is separate; no code sharing with this folder.

---

## Per-file documentation

### `config.yaml`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Static defaults for CLI and backend path resolution. |
| **Public API** | None (data file). Keys: `report_format`, `language`, `default_standard`, `sessions_dir`, `standards_root`. |
| **Inputs** | Read by `CLIConfig.load()`. |
| **Outputs** | YAML dict consumed by loader. |
| **Side effects** | None. |
| **Imported by** | `config/loader.py` (filesystem read, not Python import). |
| **Imports** | None. |
| **Actively used** | Yes, when `CLIConfig.load()` runs with default `config_path`. |
| **Confidence** | **High** |

---

### `settings.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Load `.env` files; expose environment-backed `Settings` and module singleton `settings`. |
| **Public classes/functions** | `load_env_files(*, project_root=None)`, `Settings` (frozen dataclass), `Settings.from_env()`, `settings` (module-level instance). |
| **Inputs** | `PROJECT_ROOT` env (optional), `.env` files at repo root and `desktopApp/.env`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `STANDARDS_ROOT`. |
| **Outputs** | `Settings` instance; mutates `os.environ` via `dotenv` when available. |
| **Side effects** | Calls `load_dotenv` on import (`load_env_files()` at module bottom). |
| **Imported by** | `config/loader.py`, `ai/client.py`, `tests/config/test_settings.py`. |
| **Imports** | `os`, `pathlib.Path`, optional `dotenv.load_dotenv`. |
| **Actively used** | Yes — import side effect + `settings` in `ai/client.py` and `loader.py`. |
| **Confidence** | **High** |

---

### `loader.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Merge YAML defaults and environment into a single `CLIConfig` for the application. |
| **Public classes/functions** | `CLIConfig` (frozen dataclass), `CLIConfig.load(*, config_path, env, project_root)`, `CONFIG_PATH` constant. |
| **Inputs** | `config.yaml` (or override path), `Settings` (default `settings`), optional `project_root`, `DESKTOP_USER_DATA` env. |
| **Outputs** | `CLIConfig` with resolved `Path` objects for `sessions_dir` and `standards_root`. |
| **Side effects** | File read only. |
| **Imported by** | See [Who depends on this folder](#who-depends-on-this-folder). |
| **Imports** | `config.settings` (`Settings`, `settings`), `yaml`, `os`, `pathlib`. |
| **Actively used** | Yes — central config object for API and CLI. |
| **Confidence** | **High** |

---

## Execution traces

### Desktop app task workflow

```
User opens desktop app
    ↓
desktopApp/electron/services/backendProcess.ts (sets DESKTOP_USER_DATA)
    ↓
python -m api.server
    ↓
api/desktop_service.py → DesktopApiService.from_project_root()
    ↓
config/loader.py → CLIConfig.load()
    ↓
api/workflow_bootstrap.py → standards_reader_for_config(config)
    ↓
engine/reference/standards_reader.py (uses config.standards_root)
```

### Desktop chat session

```
api/chat_service.py
    ↓
api/chat_orchestrator.py (ChatOrchestrator)
    ↓
get_config() → CLIConfig.load() via api/desktop_service.py
```

### OpenAI calls

```
ai/client.py (import)
    ↓
config/settings.py → load_env_files() + settings singleton
    ↓
OpenAIClient uses settings.openai_api_key, openai_model, openai_base_url
```

---

## Duplicate implementations

| Area | Implementations | Notes |
|------|-----------------|-------|
| Backend vs frontend config | `config/` (Python) vs `desktopApp/src/config/` (TypeScript) | Separate concerns; desktop passes env vars to Python backend. |
| Standards root | `config.yaml` `standards_root`, `Settings.standards_root` (`STANDARDS_ROOT` env), hardcoded fallbacks in some API helpers | `CLIConfig.standards_root` is authoritative at runtime for services using `CLIConfig`; `Settings.standards_root` may be redundant. **Do not infer intended design.** |

---

## Dead code (detail)

### `Settings.standards_root`

- **Why unreachable for CLIConfig path**: `CLIConfig.load()` never reads `env.standards_root`.
- **What may have used it**: Unknown from static analysis; possibly planned env override never wired.
- **Confidence**: **High** for unused in current merge path; **Low** for whether any external code reads `settings.standards_root` directly (grep found none).
