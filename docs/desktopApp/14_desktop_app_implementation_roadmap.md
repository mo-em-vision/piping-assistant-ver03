
# Desktop App Implementation Roadmap

## 1. Purpose

This document defines the recommended implementation order for the desktop application.

The goal is to build a stable MVP while avoiding:

- unnecessary complexity
- frontend/backend duplication
- architectural drift
- incomplete features

The application should be developed incrementally.

---

# 2. Core Development Principle

The desktop application is a presentation and interaction layer.

The backend remains responsible for:

- engineering logic
- calculations
- standards interpretation
- AI orchestration
- task state
- validation
- report generation

The frontend is responsible for:

- visualization
- user interaction
- rendering backend outputs
- collecting user inputs
- managing UI state

---

# 3. MVP Target

The first complete MVP should demonstrate:

```

Open Application

↓

Connect Backend

↓

Create Project

↓

Create Task

↓

Receive Task State

↓

Guide User Through Inputs

↓

Display Results

↓

Generate Report

```

---

# 4. Implementation Phases

---

# Phase 0 — Project Initialization

Goal:

Create stable desktop application foundation.

Tasks:

- create Electron project
- create React frontend
- configure build system
- configure development scripts
- create folder structure
- configure environment variables

Expected output:

Application opens successfully.

---

# Phase 1 — Desktop Shell

Goal:

Create the application window and base layout.

Implement:

- Electron window
- application menu
- startup process
- backend startup handling

Structure:

```

Desktop App

├── Electron Process  
├── React Renderer  
└── Backend Connection

```

Success criteria:

Application launches reliably.

---

# Phase 2 — Main Layout

Goal:

Implement the three-panel workspace.

Layout:

```

---

## | Left Panel | Center Workspace | Right Panel |

```

---

## Left Panel

Contains:

- create task
- available tasks
- recent tasks
- projects

Initial implementation:

Simple list views.

---

## Center Panel

Inactive:

AI/general workspace.

Active task:

Task interaction workspace.

Contains:

- inputs
- outputs
- visualizations
- reports

---

## Right Panel

Hidden by default.

Visible when task exists.

Contains:

- task state
- progress
- parameters
- AI assistance

---

# Phase 3 — Backend Connection Layer

Goal:

Connect frontend to existing backend.

Implement:

- API client
- connection handling
- request manager
- response parser

Frontend should receive:

- task state
- available options
- outputs
- errors

---

# Phase 4 — State Visualization

Goal:

Render backend state.

Implement:

- state manager
- timeline
- task progress
- status indicators

Example:

```

✓ Material: A106

✓ Pressure: 8 bar

→ Thickness

○ Report

```

---

# Phase 5 — Input System

Goal:

Create controlled engineering input interface.

Inputs supported:

- number
- text
- dropdown
- multi-select
- checkbox
- material selector
- unit selector

Rules:

Frontend receives:

- parameter name
- type
- allowed values
- default values
- units

from backend.

Frontend does not define engineering rules.

---

# Phase 6 — Output Rendering Engine

Goal:

Convert backend responses into beautiful UI.

Supported outputs:

## Text

Rendered clearly.

---

## Equations

Use:

- KaTeX
- mathematical rendering

---

## Tables

Use:

- sortable tables
- searchable tables

---

## Graphs

Support:

- engineering plots
- curves
- charts

---

## References

Display:

- standard name
- paragraph
- table
- figure

---

# Phase 7 — AI Chat Interface

Goal:

Create separated AI assistance.

Behavior:

When task inactive:

```

Center:

AI Chat

```

When task active:

```

Center:

Task workspace

Right:

AI assistance

```

---

AI messages should include:

- current task context
- state information
- relevant outputs

---

# Phase 8 — Project and Task Storage

Goal:

Persist user work.

Structure:

```

Projects

└── Project

```
└── Tasks

    ├── Chat

    ├── State

    ├── Reports

    └── Visualizations
```

```

---

Storage:

Use:

SQLite/local database.

---

# Phase 9 — Report Integration

Goal:

Connect existing backend report generation.

Frontend responsibilities:

- request report
- display status
- preview output
- export file

---

# Phase 10 — Error Handling ✅

Implemented:

- backend unavailable message (`ConnectionErrorBanner` + Electron header retry)
- invalid input message (API `recovery` payload + `ErrorBanner` in parameter form)
- failed calculation state (`task_state.errors` for invalidated tasks + `TaskErrorList`)
- retry options (connection, workspace, task refresh, chat/report reload)

Errors explain:

- what happened
- possible reason
- next action

**Backend:** `api/error_catalog.py` enriches all API error responses with `recovery` metadata; invalidated tasks expose `calculation_failed` in `task_state.errors`.

**Frontend:** `ErrorBanner`, `ConnectionErrorBanner`, `TaskErrorList`, `services/errors/errorMapper.ts`, stores use `userError: UserFacingError`.

---

# Phase 11 — Testing Integration ✅

Implemented:

## Component tests

Vitest + Testing Library coverage for:

- **buttons** — `ErrorBanner` retry, `ChatInput` send
- **inputs** — `TextInput`, `CheckboxInput`
- **viewers** — `TextOutput`, `OutputRenderer`, `StatusIndicator`

## Integration tests

- `errorMapper` and `taskStateManager` unit coverage
- `taskStore` API loading and error mapping with mocked `fetch`
- End-to-end workflow via stores: create task → submit input → generate report

## E2E tests

Playwright spec (`tests/e2e/engineeringWorkflow.spec.ts`) runs against `vite --mode test` (`VITE_MOCK_DATA=true`):

```
Create task → Input values → Calculation outputs → Report
```

**Tooling:** `vitest.config.ts`, `playwright.config.ts`, `npm run test`, `npm run test:run`, `npm run test:e2e`, `npm run dev:test`

**Note:** Playwright E2E requires `npx playwright install` on the developer machine. A Vitest UI workflow test (`engineeringWorkflow.ui.test.tsx`) covers the same path when browsers are unavailable.

---

# Phase 12 — Packaging ✅

Prepared Windows desktop installer via **electron-builder** (NSIS).

Includes:

- **Electron app** — `dist/` + `dist-electron/` packaged in the installer
- **Backend runtime** — staged Python project + bundled `.venv` under `resources/backend`
- **Resources** — `standards/` and backend packages copied at build time

Startup (unchanged flow, now production-ready):

```
Open App → Start Backend → Connect Frontend
```

**Build commands** (from `desktopApp/`):

```bash
npm run stage:backend      # copy api/engine/models/... into resources/backend
npm run prepare:backend    # create bundled .venv (Windows PowerShell)
npm run package:win        # stage + venv + vite build + NSIS installer
```

Installer output: `desktopApp/release/`

**User data:** backend receives `DESKTOP_USER_DATA` (Electron `userData` / AppData) so SQLite and sessions are not written under Program Files.

---

# Phase 13 — MVP Verification ✅

Validated the MVP completion criteria (roadmap Section 15):

| Criterion | Verification |
| --- | --- |
| 1. Open application | Electron shell, backend startup, health connection |
| 2. Create/select project | `projectStore` + project API; `test_mvp_project_task_and_input_collection` |
| 3. Start engineering task | Task create/activate; UI + API tests |
| 4. Provide inputs | `ParameterForm` + `submit_input` API |
| 5. Receive backend results | Task state refresh after input submission |
| 6. View calculations | `display_outputs` + `OutputRenderer`; completed workflow test |
| 7. Generate report | `ReportPanel` + `test_mvp_calculation_outputs_and_report` |

**Automated verification:**

```bash
cd desktopApp
npm run verify:mvp
```

Runs frontend workflow integration/UI tests and `tests/mvp/test_desktop_mvp_workflow.py` backend MVP contract tests.

**MVP status:** Complete — pipe wall thickness workflow is end-to-end from project creation through report generation.

---

# Phase 14 — Cursor Implementation Rules ✅

Codified roadmap Section 14 and `13_frontend_development_workflow_with_cursor.md` as enforceable project guidance:

| Artifact | Purpose |
| --- | --- |
| `AGENTS.md` | Root agent entry point — docs, boundaries, test commands, key paths |
| `.cursor/rules/desktop-project.mdc` | Always-on workflow, architecture boundaries, verification |
| `.cursor/rules/desktop-frontend.mdc` | `desktopApp/**` — stores, API client, components, Electron |
| `.cursor/rules/backend-engine.mdc` | Python API/engine — contracts, errors, persistence |

**Cursor should:**

Before coding — read documentation, inspect existing code, propose plan.

During coding — keep backend boundaries, avoid unnecessary libraries, maintain tests.

After coding — explain changes, identify risks.

`.gitignore` updated so `.cursor/rules/` is committed while other `.cursor/` machine state stays local.

---

# Phase 15 — MVP Completion & Release Readiness ✅

Formalized roadmap Section 15 (MVP completion) and deployment §27 (release process).

### MVP completion (Section 15)

All seven user capabilities are implemented and covered by `npm run verify:mvp` (Phase 13).

### Release readiness

| Check | Implementation |
| --- | --- |
| Application startup | Electron bootstrap + logging |
| Backend connection | `BackendProcessService` + health polling |
| Main workflows | MVP integration/UI tests |
| Reporting | Report API + `ReportPanel` |
| Error handling | Phase 10 `ErrorBanner` + recovery metadata |

### Polish & support

- **`electron/services/appLogger.ts`** — logs to `%AppData%/…/logs/desktop.log`
- **Help menu** — Open Logs Folder, Copy Diagnostics (version, backend status, log path)
- Backend stderr captured in the log file

### Automated release verification

```bash
cd desktopApp
npm run verify:release
```

Runs TypeScript check, MVP smoke tests, release readiness tests, and Cursor rules tests.

**Release build:** `npm run package:win` → installer in `desktopApp/release/`

---

# 13. Development Order Rule

Features should be built in this order:

1. Structure
2. Data flow
3. Backend connection
4. Visualization
5. Interaction
6. Polish

Avoid:

Building beautiful UI without working data flow.

---

# 14. Cursor Implementation Rules

Cursor should:

Before coding:

- read documentation
- inspect existing code
- propose plan

During coding:

- keep backend boundaries
- avoid unnecessary libraries
- maintain tests

After coding:

- explain changes
- identify risks

---

# 15. MVP Completion Definition

MVP is complete when:

User can:

1. open application
2. create/select project
3. start engineering task
4. provide inputs
5. receive backend results
6. view calculations
7. generate report

---

# 16. Future Expansion

After MVP:

Possible additions:

- cloud backend
- authentication
- collaboration
- company databases
- multiple disciplines
- mobile client

---

# Final Principle

Build the smallest complete engineering workflow first.

The goal is not a perfect desktop application.

The goal is proving that engineers can complete real design tasks faster and more reliably.
```

Your documentation set now covers:

1. Vision
    
2. Architecture
    
3. UI/UX
    
4. AI behavior
    
5. Data flow
    
6. Component structure
    
7. Backend connection
    
8. Testing
    
9. Deployment
    
10. Cursor workflow
    
11. Implementation order
    

At this point, you have enough documentation for Cursor to start building without needing to "guess the product".