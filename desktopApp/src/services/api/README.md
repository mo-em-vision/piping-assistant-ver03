# src/services/api — Architecture Audit

Thin REST client layer over the Ver03 Python backend. All engineering behavior stays server-side; these modules only perform HTTP calls, deduplication, and light response parsing.

## Purpose

Centralize `fetch`-based access to `/api/v1/*` endpoints. `backendClient` is the single HTTP primitive; domain modules (`taskApi`, `projectApi`, etc.) add paths and types. `requestManager` deduplicates concurrent identical requests.

## Files

| File | Purpose | Key exports | Used by |
| --- | --- | --- | --- |
| `backendClient.ts` | JSON fetch wrapper, `ApiError` on non-OK | `BackendClient`, `backendClient` | All `*Api.ts`, `connectionStore`, `devStudioApi` |
| `requestManager.ts` | In-flight promise cache by string key | `RequestManager`, `requestManager` | Most `*Api.ts` (not `standardsApi`, `inspectionApi`, `materialApi` direct calls) |
| `responseParser.ts` | DTO → UI summary helpers | `parseTaskState`, `projectToSummary`, `workflowToSummary`, `toNavTaskSummary`, … | `taskStore`, `projectStore`, `taskApi`, `inputApi` |
| `taskApi.ts` | Tasks, workflows, recent tasks | `taskApi` | `taskStore` |
| `projectApi.ts` | Project CRUD / activate | `projectApi` | `projectStore` |
| `inputApi.ts` | Submit parameter, edit preview/begin | `inputApi` | `taskStore`, `RightPanel` |
| `chatApi.ts` | List/send/clear chat | `chatApi` | `chatStore` |
| `reportApi.ts` | Report status, generate, preview, download | `reportApi` | `reportStore` |
| `standardsApi.ts` | Browse, node, table sources | `standardsApi` | Standards components, tests |
| `materialApi.ts` | Warm catalog, search, detail | `materialApi` | `materialCatalogStore`, `MaterialSearchInput`, `MaterialReferenceTab` |
| `inspectionApi.ts` | Dev inspection payload, breakpoints, replay | `inspectionApi` | `useInspectionPayload`, `InspectorPanels` |
| `taskContinuationApi.ts` | GET continuation suggestions | `taskContinuationApi` | **None** (see Dead Code) |

### Per-file inventory

**`backendClient.ts`** — Confidence: **High**
- Inputs: path, `RequestOptions` (body, timeout default 15s)
- Outputs: parsed JSON or throws `ApiError`
- Imports: `@/config/env`, `@/types/backend/apiError`, `@/types/backend/api`
- Base URL from `env.backendUrl`

**`requestManager.ts`** — Confidence: **High**
- `run(key, task)` returns shared promise for same key until settled
- `clear()` exists but grep shows no callers outside file — **Low** dead-code risk for `clear()` only

**`taskContinuationApi.ts`** — Confidence: **High** (unused module)
- `GET /api/v1/tasks/{taskId}/continuation-suggestions`
- No store or component imports this export

## Entry Points

No file is executed standalone. Consumers import named singletons:

- Stores: `taskStore`, `projectStore`, `chatStore`, `reportStore`, `materialCatalogStore`, `connectionStore`
- Components: `RightPanel`, standards tabs, inspector panels
- Dev Studio: `devStudioApi` reuses `backendClient`

## Dependencies

**Depends on:**

- `@/config/env` — `backendClient` base URL
- `@/types/backend/*` — request/response shapes
- Browser `fetch` / `AbortSignal.timeout`

**Depended on by:**

- `src/store/*` (except `rightPanelStore`, `uiStore`, `taskStateManager`)
- `src/dev-studio/api/devStudioApi.ts`
- `src/components/standards/*`, `dev/desktop_ui/inspector/*`
- `tests/` (mocked or real module imports)

## Runtime Usage

**Active** whenever `VITE_MOCK_DATA !== 'true'` and backend is reachable.

**Bypassed** in mock mode: stores short-circuit before calling APIs (except `connectionStore.checkApiConnection` which still hits health).

**Inspection API** only used when `env.devMode` loads `DeveloperInspector` and user opens Inspector.

## Possible Dead Code

| File / symbol | Evidence | Confidence |
| --- | --- | --- |
| `taskContinuationApi.ts` | Zero imports outside file | High |
| `requestManager.clear()` | No callers | Medium |
| `responseParser.parseProjects` | Used by `projectApi`; **High** active | — |

## Notes

- `standardsApi` and `materialApi` call `backendClient.request` directly (no `requestManager`) — duplicate in-flight requests possible for rapid re-clicks.
- `inspectionApi` also skips `requestManager`.
- `reportApi.generate` uses 90s timeout; others default 15s.
- Session scoping: most task/project endpoints append `?session_id=` from `getActiveSessionId()` in stores.

## Execution Traces

### Load active task state

```
taskStore.loadWorkspace / selectTask / refreshActiveTask
  → taskApi.get(taskId, sessionId)
  → requestManager.run('tasks:get:…')
  → backendClient.get('/api/v1/tasks/{id}?session_id=…')
  → parseTaskState
  → taskStore.applyTaskState
```

### Submit parameter

```
taskStore.submitParameter
  → inputApi.submit(taskId, { parameter, value, unit }, sessionId)
  → POST /api/v1/tasks/{id}/inputs
  → parseTaskState → applyTaskState
  (optimistic: applyOptimisticParameterSubmit before await in taskStore)
```

### Standards browse tab

```
StandardsBrowserTab mount
  → standardsApi.getBrowse('asme_b31.3')
  → GET /api/v1/standards/browse?standard=…
  → StandardsBrowserTree render
```

### Chat send

```
chatStore.sendMessage
  → chatApi.send(payload, sessionId)
  → POST /api/v1/chat/messages
  → taskStore.applyTaskState if response includes task_state
```

### Health check (parallel to Electron backend health)

```
connectionStore.checkApiConnection
  → fetch(buildHealthUrl(backendClient.getBaseUrl()))
  (does not use backendClient.request)
```
