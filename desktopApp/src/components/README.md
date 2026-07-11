# src/components — Architecture Audit

React UI for the Engineering Workspace. Components render backend `task_state`, collect input, and drive API calls **only through Zustand stores** (or local fetch for standards tabs). No engineering validation logic belongs here.

**Audit scope:** Subfolder summary with file counts and key entry components. Individual files are grouped; not every file has a separate inventory line.

## Purpose

Organize the three-panel workspace (left nav, center workflow, right references/chat/task) plus shared building blocks for outputs, inputs, standards browsing, errors, and development tools.

## Subfolders

| Subfolder | Files | TS/TSX | Key entry components | Role |
| --- | ---: | ---: | --- | --- |
| `layout/` | 18 | 9 | `WorkspaceLayout`, `LeftPanel`, `CenterPanel`, `RightPanel`, `AppHeader` | Shell, resize, panel chrome |
| `workflow/` | 15 | 9 | `WorkflowComposer`, `WorkflowHeader`, `WorkflowHistory`, `TaskCompletionNextSteps` | Active task workflow UI |
| `standards/` | 21 | 12 | `StandardsBrowserTab`, `StandardsMarkdownViewer`, `NodeReferenceTab`, `TableReferenceTab` | Standards browse + reference tabs |
| `inputs/` | 13 | 9 | `ParameterForm`, `ParameterInput`, `MaterialSelector` | Parameter input widgets |
| `outputs/` | 12 | 9 | `OutputRenderer`, `TextOutput`, `EquationOutput`, `NextWorkflowsOutput`, `ReferenceChipList` | `display_outputs` + transcript block rendering |
| `engineering/` | 12 | 6 | `TaskTimeline`, `TimelineStep`, `NodeCalculationGroup` | Progress/timeline/calculations |
| `chat/` | 8 | 5 | `ChatPanel`, `ChatMessage`, `ChatInput` | Right-panel and center chat |
| `errors/` | 5 | 3 | `ErrorBanner`, `ConnectionErrorBanner`, `TaskErrorList` | User-facing errors |
| `tasks/` | 6 | 3 | `CreateTaskDialog`, `RecentTaskRow`, `TaskContextMenu` | Task list actions |
| `projects/` | 4 | 2 | `ProjectGroup`, `CreateProjectDialog` | Project sidebar |
| `reports/` | 2 | 1 | `ReportPanel` | Report preview in right panel |
| `math/` | 2 | 1 | `engineeringMath` | KaTeX/markdown math |
| `common/` | 1 | 1 | `RenameDialog` | Shared rename modal |
| `ui/` | 2 | 1 | `ExternalLink` | External link with icon |

**Total:** ~117 files under `components/` (including CSS). Inline dev UI lives in `dev/desktop_ui/` (imported via `@dev-ui/*`).

## Entry Points

Components are not standalone executables. Top of render tree:

```
App.tsx
  → DevNodeHoverProvider (@dev-ui/)
  → WorkspaceLayout (layout/)
      → AppHeader, LeftPanel, CenterPanel, RightPanel
```

Lazy entry (dev only):

```
WorkspaceLayout → lazy(@dev-ui/inspector/DeveloperInspector) when env.devMode
RightPanel → lazy(@dev-ui/NodeEditTab) when node edit tab open
```

## Dependencies

**Depends on:**

- `@/store/*` — primary state
- `@/hooks/*` — `useActiveTaskViewModel`, `useWindowDisplayState`
- `@/services/api/*` — direct use in `RightPanel` (`inputApi`), standards tabs (`standardsApi`, `materialApi`), inspector (`inspectionApi`)
- `@/types/*`, `@/utils/*`, `@/templates/*`
- `@/config/env` — dev gating

**Depended on by:**

- `App.tsx`
- Extensive `tests/components/**`

## Runtime Usage

**Always on main path:** `layout/*`, `workflow/*` (when task active), `errors/ConnectionErrorBanner`, `projects/*`, `tasks/*`, parts of `chat/*`.

**Conditional:**

- `@dev-ui/inspector/DeveloperInspector` — `env.devMode` only (see `dev/desktop_ui/`)
- `@dev-ui/DevNodeHoverProvider` — always mounted; hover UI checks dev flags internally
- `reports/ReportPanel` — right panel when report section visible
- `standards/*` — right panel standards/reference tabs

## Possible Dead Code

| Item | Location | Evidence | Confidence |
| --- | --- | --- | --- |
| `TaskProgress` | `engineering/TaskProgress.tsx` | No imports outside file | High |
| `taskContinuationApi` consumers | N/A | No UI for continuation suggestions yet | High (API layer, not component) |

All other subfolders have tested, wired entry components.

## Notes

- **Center vs right chat:** `CenterPanel` embeds `ChatPanel` in some states; `RightPanel` also hosts chat tab — two hosts, one `chatStore`.
- **Output pipeline:** `OutputRenderer` dispatches by block `kind` to `outputs/*`; `TextOutput` integrates dev hover and reference links.
- **Standards duplication:** Browse UI (`StandardsBrowserTab`) vs deep-linked reference tabs (`NodeReferenceTab`, `TableReferenceTab`, `MaterialReferenceTab`) share `standardsApi` but different component trees.
- **CSS co-location:** Most subfolders pair `.tsx` + `.css`; `workflow/WorkflowPanel.css` imported from `CenterPanel`.
- **Center panel scroll contract (Phases 1–6):** `CenterPanel` merges `flow_guidance.transcript_blocks` + `display_outputs` via `buildCenterPanelTranscript` (`src/utils/buildCenterPanelTranscript.ts`). Shared block order comes from `contracts/center_panel_report_role_order.json` (imported in `centerPanelContract.ts`). Composer stays on `current_ask.short_prompt` only — not merged into scroll history. See `docs/desktopApp/center_panel_output_contract.md`.

---

## Subfolder detail

### `layout/` (18 files)

| File | Purpose |
| --- | --- |
| `WorkspaceLayout.tsx` | Three-column grid, resize handles, lazy inspector slot |
| `AppHeader.tsx` | Title, backend status, inspector toggle, reload |
| `LeftPanel.tsx` | Projects, tasks, recent tasks, rename dialogs |
| `CenterPanel.tsx` | Workflow composer/history or empty state; task errors; scroll via `buildCenterPanelTranscript` |
| `RightPanel.tsx` | Tabbed: task details, chat, standards, dynamic references |
| `ResizeHandle.tsx` | Drag to resize side panels |
| `PanelSection.tsx` | Collapsible section wrapper |
| `SidePanelContextMenu.tsx` | Context menu (e.g. Ask AI) |
| `SidePanelRowActions.tsx` | Row action buttons |
| `RightPanelTabIcon.tsx` | Tab icons and ARIA labels |
| `*.css` | Layout styles |

**Trace — layout mount:**

```
WorkspaceLayout
  → LeftPanel (projectStore, taskStore)
  → CenterPanel (taskStore, chatStore, workflow)
  → RightPanel (rightPanelStore, multiple tab bodies)
```

### `workflow/` (15 files)

| File | Purpose |
| --- | --- |
| `WorkflowComposer.tsx` | Renders backend ask prompt and input for submittable parameters |
| `ComposerInput.tsx` / `ComposerInlineInput.tsx` | Text/inline composers |
| `MaterialSearchInput.tsx` | Material parameter search |
| `WorkflowHeader.tsx` | Active node context header |
| `WorkflowHistory.tsx` | Past steps + outputs in timeline |
| `buildWorkflowHistory.ts` | Maps `display_outputs` to history items |
| `workflowAsk.ts` | Resolves backend-driven ask prompt + submittable parameter |
| `optimisticWorkflowTransition.ts` | Optimistic UI before API returns |
| `TaskCompletionNextSteps.tsx` | Post-completion report actions |

**Trace — parameter submit:**

```
WorkflowComposer → taskStore.submitParameter
  → (optimisticWorkflowTransition) → inputApi
```

### `standards/` (21 files)

| File | Purpose |
| --- | --- |
| `StandardsBrowserTab.tsx` | Main browse entry |
| `StandardsBrowserTree.tsx` / `Sidebar.tsx` / `Preview.tsx` | Tree navigation |
| `StandardsMarkdownViewer.tsx` | Renders node markdown |
| `StandardsTableViewer.tsx` | Table data grid |
| `NodeReferenceTab.tsx` / `TableReferenceTab.tsx` / `MaterialReferenceTab.tsx` | Right-panel reference views |
| `StandardReferenceLink.tsx` | Clickable refs from outputs |
| `standardsBrowseUtils.ts` / `standardsReferenceLinks.ts` | Helpers |

### Inline dev UI (`dev/desktop_ui/`)

Moved out of `components/` for consistency with other dev tooling. See [`dev/desktop_ui/README.md`](../../../../dev/desktop_ui/README.md).

| File | Purpose |
| --- | --- |
| `DevNodeHoverProvider.tsx` | Context for node provenance hover |
| `DevNodeHoverSurface.tsx` / `DevNodeTooltip.tsx` | Hover UI on outputs |
| `NodeEditTab.tsx` | Right-panel YAML edit tab |
| `inspector/DeveloperInspector.tsx` | Floating inspector shell |
| `inspector/*` | Inspector panels, store, hooks |

### `inputs/` (13 files)

Typed inputs driven by `ParameterDefinitionDto`: `ParameterForm` → `ParameterInput` → `TextInput` | `NumberInput` | `DropdownInput` | `CheckboxInput` | `MultiSelectInput` | `UnitSelector` | `UnitPillGroup` | `MaterialSelector`.

### `outputs/` (8 files)

`OutputRenderer` → `TextOutput` | `EquationOutput` | `TableOutput` | `GraphOutput` | `ResultOutput` | `ReferenceOutput`.

### `engineering/` (12 files)

`TaskTimeline` + `TimelineStep` + `StatusIndicator` + `NodeCalculationGroup` + `ParameterEditDialog`. **`TaskProgress.tsx` appears unused.**

### `chat/` (8 files)

`ChatPanel` orchestrates `ChatMessage`, `ChatInput`, `ChatPendingReply`, `ChatMarkdownContent`.

### `errors/` (5 files)

`ConnectionErrorBanner` (backend/Electron), `ErrorBanner` (generic `UserFacingError`), `TaskErrorList` (API error list in center).

### `tasks/`, `projects/`, `reports/`, `math/`, `common/`, `ui/`

Smaller scoped folders — see table above. `ReportPanel` uses `reportStore`; `RenameDialog` used from `LeftPanel`.

---

## Execution Traces

### Full UI path (active task)

```
WorkspaceLayout
  → CenterPanel
      → WorkflowHeader
      → WorkflowHistory (buildCenterPanelTranscript → buildWorkflowHistory items)
      → WorkflowComposer (ParameterForm → inputs/*)
      → Output blocks via history items → OutputRenderer (text, equation, next_workflows, …)
  → RightPanel
      → Task tab: TaskTimeline, NodeCalculationGroup, ParameterEditDialog
      → Chat tab: ChatPanel
      → Standards tab: StandardsBrowserTab
```

### Open reference from output

```
TextOutput / StandardReferenceLink
  → rightPanelStore.openReferenceTab
  → RightPanel → NodeReferenceTab | TableReferenceTab
  → standardsApi.getNode | getTable
  → StandardsMarkdownViewer | StandardsTableViewer
```

### Ask AI on selection

```
CenterPanel contextmenu
  → chatStore.askAboutSelection
  → rightPanelStore (may open chat)
  → chatApi.send (mode: selection_explain)
```

### Dev inspector

```
AppHeader → toggle inspector
  → DeveloperInspector
  → useInspectionPayload → inspectionApi.get
  → ExecutionTracePanel | PlannerPanel | ValueProvenancePanel | InspectorGraphPanel
```

### Create task

```
LeftPanel / uiStore.createTaskDialog
  → CreateTaskDialog
  → taskStore.createTask → taskApi.create
```
