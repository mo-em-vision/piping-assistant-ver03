# src/types — Architecture Audit

TypeScript contracts between the desktop renderer and the Ver03 REST API, plus frontend-only view models and Electron window typings.

## Purpose

| Subfolder | Role |
| --- | --- |
| `backend/` | Shapes mirroring API JSON (DTOs, error bodies) |
| `frontend/` | UI view models, workspace summaries, Electron bridge types |

No runtime logic except `apiError.ts` (`ApiError` class) and re-exports in `errors.ts`.

## Files

### `backend/`

| File | Purpose | Key types | Importers (sample) |
| --- | --- | --- | --- |
| `api.ts` | Core API DTOs | `TaskStateDto`, `WorkflowDto`, `ProjectDto`, `NodeProvenanceDto`, `StandardsBrowseNodeDto`, `mapBackendStatus` | Stores, components, `responseParser` |
| `apiError.ts` | HTTP error class | `ApiError`, `isApiError` | `backendClient`, `errorMapper` |
| `errors.ts` | Re-export barrel | Re-exports `ApiError`, `toUserFacingError` | Stores, components |
| `chat.ts` | Chat DTOs | `ChatMessageDto`, `SendChatPayload`, `ChatContextDto` | `chatStore`, `chatApi`, chat components |
| `parameters.ts` | Input definitions | `ParameterDefinitionDto`, `SubmitInputPayload` | Inputs, workflow, `inputApi` |
| `outputs.ts` | Display output blocks | `TextOutputBlock`, `EquationOutputBlock`, `DisplayOutputBlock`, … | Output renderers, `mergeDisplayOutputs` |
| `reports.ts` | Report DTOs | `ReportSummaryDto`, `ReportPreviewDto`, `GenerateReportPayload` | `reportStore`, `reportApi` |
| `materials.ts` | Material catalog | `MaterialOptionDto`, `MaterialDetailDto` | `materialApi`, material UI |
| `inspection.ts` | Dev inspector payload | `InspectionPayloadDto`, `ExecutionTraceStepDto`, `InspectorTabId` | Inspector components, `inspectionApi` |
| `continuation.ts` | Task next-workflow suggestions | `TaskContinuationSuggestionsDto` | **Only** `taskContinuationApi.ts` |

### `frontend/`

| File | Purpose | Key types | Importers |
| --- | --- | --- | --- |
| `workspace.ts` | Nav summaries | `TaskSummary`, `ProjectSummary`, `TaskStatus` | Left panel, tasks, stores |
| `taskState.ts` | View models | `TaskStateViewModel`, `TimelineStepViewModel`, `StatusVariant` | `taskStateManager`, engineering/workflow UI |
| `userError.ts` | Normalized UI errors | `UserFacingError` | Error banners, stores |
| `electron.d.ts` | `window.electronAPI` | `ElectronAPI`, global `Window` augmentation | `useBackend`, `useWindowDisplayState`, preload consumers |

### Per-file confidence

All files except `continuation.ts` show multiple production importers — **High** active use.

## Entry Points

Types are compile-time only. `ApiError` in `apiError.ts` is instantiated at runtime by `backendClient`.

`electron.d.ts` is ambient/global; no import required.

## Dependencies

**Internal type graph:**

```
api.ts → outputs.ts, parameters.ts, workspace.ts
outputs.ts → api.ts (NodeProvenanceDto)
parameters.ts → api.ts
chat.ts → api.ts
apiError.ts → api.ts
errors.ts → apiError.ts, services/errors/errorMapper
```

**Depends on:**

- `src/services/errors/errorMapper.ts` (`errors.ts` re-export only — unusual coupling of types → services)

**Depended on by:**

- Entire `src/store`, `src/services/api`, most `src/components`
- `electron/preload.ts` (via `constants` types, not this folder directly except electron.d.ts pattern)
- Tests and mocks

## Runtime Usage

**Active:** All DTOs used when parsing API responses.

**Inactive / dormant:** `continuation.ts` types — API client exists but no UI consumer.

## Possible Dead Code

| File | Evidence | Confidence |
| --- | --- | --- |
| `backend/continuation.ts` | Only imported by unused `taskContinuationApi.ts` | High |

## Notes

- **Duplicate error pathways:** `UserFacingError` (frontend) vs `ApiErrorBody` (backend) vs `ApiError` class — mapped in `services/errors/errorMapper.ts`.
- **`errors.ts` imports service code** — types folder is not pure types; `toUserFacingError` lives in services.
- `TaskStatus` exists in both `workspace.ts` (frontend) and mapped from backend strings via `mapBackendStatus` in `api.ts`.
- `taskState.ts` uses inline `import()` type for provenance to avoid circular refs.

## Execution Traces

### API error → UI banner

```
backendClient.request → throws ApiError (apiError.ts)
  → store catch → toUserFacingError (errors.ts → errorMapper)
  → ErrorBanner / ConnectionErrorBanner (UserFacingError)
```

### Task state → timeline UI

```
GET /api/v1/tasks/{id} → TaskStateDto (api.ts)
  → taskStore.activeTaskState
  → buildTaskStateViewModel → TaskStateViewModel (taskState.ts)
  → TimelineStep, WorkflowHistory, CenterPanel
```

### Display outputs

```
TaskStateDto.display_outputs: DisplayOutputBlock[] (outputs.ts)
  → mergeDisplayOutputs (utils)
  → OutputRenderer → TextOutput | EquationOutput | …
```

### Electron IPC typing

```
preload exposes BackendStatusPayload (from config/constants, not types/)
window.electronAPI typed via electron.d.ts
  → useBackendConnection
```
