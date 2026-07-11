# Architecture Audit — Repository Root

Static audit of the Ver03 repository root. User onboarding remains in [README.md](README.md).

## Purpose

Top-level entry points and layout for the **Python engineering backend** plus **Electron + React desktop client** (`desktopApp/`). Engineering logic lives in `engine/`; the desktop app is a thin presentation layer.

## Top-Level Layout

| Path                       | Role                                                                                 |
| -------------------------- | ------------------------------------------------------------------------------------ |
| [api/](api/)               | REST server for desktop (`python -m api.server`)                                     |
| [engine/](engine/)         | Graph, planner, validation, execution, reports                                       |
| [ai/](ai/)                 | LLM agents for navigation and explanation only                                       |
| [models/](models/)         | Shared dataclasses / enums                                                           |
| [storage/](storage/)       | Desktop SQLite project persistence                                                   |
| [desktopApp/](desktopApp/) | Electron + React client                                                              |
| [knowledge/](knowledge/) | Engineering knowledge: `standards/` packs + `global/` ontologies |
| [config/](config/)         | `config.yaml` + env settings → `CLIConfig`                                           |
| [scripts/](scripts/)       | Offline DB builders and migrations                                                   |
| [tests/](tests/)           | Backend pytest suite                                                                 |
| [dev/](dev/)               | Dev-only tools (desktop dev UI)                                                      |
| [docs/](docs/)             | Design docs, audit progress, node templates                                          |
| [AGENTS.md](AGENTS.md)     | Agent/developer guide                                                                |

## Entry Points

| File                                                       | How invoked                        | Next hop                                         |
| ---------------------------------------------------------- | ---------------------------------- | ------------------------------------------------ |
| [api/server.py](api/server.py)                             | `python -m api.server`             | [api/desktop_service.py](api/desktop_service.py) |
| [desktopApp/electron/main.ts](desktopApp/electron/main.ts) | `npm run dev` / packaged app       | Spawns backend, loads renderer                   |
| [desktopApp/src/main.tsx](desktopApp/src/main.tsx)         | Vite renderer                      | React app shell                                  |

## Dependencies

**Root depends on:** `config/`, all application packages.

**Depends on root:** Developers, CI, Electron launcher (repo root resolution).

## Runtime Usage

**On execution path:** `api/server.py`, `desktopApp/` are the production entry surfaces.

**Not directly executed:** `docs/`, `scripts/` (manual/CI), `tests/` (pytest), `dev/` (optional dev tool).

## Possible Dead Code

| Item | Why | Confidence |
|------|-----|--------------|
| Root-level stray logs (e.g. `debug-b5dce6.log`) | Debug artifacts | Medium |

## Notes

- Micro-graph compile path: `knowledge/standards/*/nodes/**` → `GraphBuilder` → `PackGraph` → optional `*_graph.db`.
- Session persistence: `storage/` (SQLite + filesystem session layout via `storage/session_store.py`).
- Design docs under `docs/core/` describe intent; folder READMEs under each package document implementation.

## Execution Traces

### Desktop (primary)

```
User action (WorkflowPanel)
  → desktopApp/src/services/api/*
  → api/server.py
  → api/desktop_service.py
  → engine/planner, engine/graph, engine/executor
  → serializers.task_state
  → React components (outputs, workflow)
```

### Knowledge compile (offline)

```
knowledge/standards/**/nodes/*.yaml
  → scripts/build_graph_db.py / build_all_standards_dbs.py
  → engine/reference/graph_compile.py
  → *_graph.db, knowledge/standards/standards_config.db
```

## Per-Folder Audit Index

See [docs/audit/PROGRESS.md](docs/audit/PROGRESS.md) for status. Detailed READMEs live in each package directory.
