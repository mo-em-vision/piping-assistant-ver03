# src/store — Architecture Audit

[Zustand](https://github.com/pmndrs/zustand) stores holding client-side workspace state. Stores call `src/services/api/*` and coordinate cross-cutting UI state (panels, tabs, errors). Engineering truth remains in backend `TaskStateDto` responses.

## Purpose

| Store | Responsibility |
| --- | --- |
| `projectStore` | Project list, active project id (localStorage-backed) |
| `taskStore` | Active task, task state DTO, task lists, parameter submit |
| `chatStore` | Chat messages, send/ask-about-selection |
| `rightPanelStore` | Multi-tab right panel (task, chat, standards, references, node-edit) |
| `uiStore` | Panel widths, collapse, fullscreen, create-task dialog |
| `reportStore` | Report summary, preview, generate/download |
| `connectionStore` | Renderer-side API health (distinct from Electron backend process status) |
| `materialCatalogStore` | Material catalog warm-up flag |
| `taskStateManager` | Pure view-model builders (not a Zustand store) |

## Files

| File | Type | Key exports | Mock gate |
| --- | --- | --- | --- |
| `projectStore.ts` | Zustand | `useProjectStore`, `getActiveSessionId` | `VITE_MOCK_DATA` |
| `taskStore.ts` | Zustand | `useTaskStore` | `VITE_MOCK_DATA` |
| `chatStore.ts` | Zustand | `useChatStore` | `VITE_MOCK_DATA` |
| `rightPanelStore.ts` | Zustand | `useRightPanelStore`, tab types | No |
| `uiStore.ts` | Zustand | `useUiStore` | No |
| `reportStore.ts` | Zustand | `useReportStore` | `VITE_MOCK_DATA` |
| `connectionStore.ts` | Zustand | `useConnectionStore` | No |
| `materialCatalogStore.ts` | Zustand | `useMaterialCatalogStore` | `VITE_MOCK_DATA` |
| `taskStateManager.ts` | Pure functions | `buildTaskStateViewModel`, `isTaskCompleted`, `isReportSectionVisible` | No |

### Per-file detail

**`taskStore.ts`** — Confidence: **High**
- Imports: `inputApi`, `taskApi`, `projectStore`, `rightPanelStore`, `uiStore`, `optimisticWorkflowTransition`
- Side effects: API calls, collapses right panel when no task, `startTransition` for some updates
- Public actions: `loadWorkspace`, `selectTask`, `createTask`, `submitParameter`, `deleteTask`, `renameTask`, …

**`projectStore.ts`** — Confidence: **High**
- Persists active project via `@/services/storage/projectPreferences`
- Filters out `default` project from list
- `getActiveSessionId()` used widely as `session_id` for API calls

**`rightPanelStore.ts`** — Confidence: **High**
- Tab model: pinned `task` | `chat` | `standards` plus dynamic `reference`, `material`, `node-edit` tabs
- `reset(hasTask)` called from `taskStore` on task clear

**`taskStateManager.ts`** — Confidence: **High**
- Maps `TaskStateDto` → `TaskStateViewModel` for timeline/progress UI
- No side effects

## Entry Points

Stores are not standalone executables. Initialization path:

```
useWorkspaceBootstrap → projectStore.loadProjects → taskStore.loadWorkspace
```

Direct `getState()` calls exist (`useTaskStore.getState()`, `useProjectStore.getState()`) inside stores and hooks for imperative coordination.

## Dependencies

**Depends on:**

- `src/services/api/*`
- `src/services/storage/projectPreferences` (`projectStore` only)
- `src/types/backend/*`, `src/types/frontend/*`
- `src/mock/*` (mock mode)
- `src/components/workflow/optimisticWorkflowTransition` (`taskStore` only — store imports component util)
- `src/utils/*` (confirm dialogs, merge outputs, engineering display)

**Depended on by:**

- `src/hooks/useWorkspaceBootstrap.ts`, `useActiveTaskViewModel.ts`
- Most `src/components/layout/*`, workflow, chat, reports
- `dev/desktop_ui/DevNodeHoverProvider.tsx`, inspector hooks

## Runtime Usage

All Zustand stores are active in the main app renderer.

`connectionStore` runs on every backend-connected bootstrap; `materialCatalogStore.warmCatalog` runs once per session after health OK.

## Possible Dead Code

| Item | Evidence | Confidence |
| --- | --- | --- |
| None in store files | All 9 files have grep hits from components/hooks | High |
| `taskContinuationApi` integration | Never wired to any store | High (missing feature, not dead store code) |

## Notes

- **Cross-store coupling:** `taskStore` calls `useProjectStore.getState()`, `useRightPanelStore.getState()`, `useUiStore.setState` directly.
- **Session id naming:** `getActiveSessionId()` returns `projectStore.activeProjectId` (project id used as API `session_id`).
- **Duplicate status concepts:** Electron `BackendStatusPayload` vs `connectionStore.apiStatus` vs `taskStore.userError` — three layers of "connection health."
- `chatStore.sendMessage` can apply returned `task_state` to `taskStore` after chat round-trip.

## Execution Traces

### Bootstrap

```
useWorkspaceBootstrap
  → connectionStore.checkApiConnection
  → materialCatalogStore.warmCatalog
  → projectStore.loadProjects
  → taskStore.loadRecentTasksGlobal
  → taskStore.loadWorkspace + chatStore.loadMessages
```

### Select task (left panel)

```
LeftPanel → taskStore.selectTask(taskId)
  → ensureProjectForTask (may projectStore.selectProject)
  → taskApi.activate + taskApi.get
  → applyTaskState
  → rightPanelStore.reset(true)
  → chatStore.loadMessages
```

### Open standards reference tab

```
StandardReferenceLink → rightPanelStore.openReferenceTab
  → RightPanel renders reference tab component
  (no store beyond tab state)
```

### Task completed → report

```
CenterPanel → TaskCompletionNextSteps
  → reportStore.loadReport / generateReport / downloadReport
```

### Build timeline view model

```
useActiveTaskViewModel
  → taskStore.activeTaskState
  → buildTaskStateViewModel (taskStateManager)
  → CenterPanel, RightPanel consume viewModel
```
