# Developer Inspection Framework

Development-only debugging environment for verifying that the application executes entirely through the **knowledge graph**. Provides execution trace, value provenance, planner explanations, live graph overlay, integrity checks, and execution replay.

The framework does **not** ship in production builds and does **not** change planner or business logic.

**Related tools:** [Node Dev Studio](node_dev_studio.md) (node authoring), inline dev hovers (`DevNodeHoverSurface`).

---
## maintaining Audit Files
after each change "update `@audit engine/executor/README.md#files` for the new module”

---

## 1. Purpose

The Developer Inspector answers: *“Where did this value come from, and why did the planner run this node?”*

| Capability | What it shows |
|------------|----------------|
| **Execution Trace** | Per-node stack trace: inputs, outputs, duration, status, selection reason |
| **Value Provenance** | Source node, property, upstream/downstream graph links, transformation history |
| **Planner** | Why each node was selected, edge followed, rejected candidates |
| **Graph** | Active subgraph summary in the inspector layout |
| **Replay** | Step through stored execution frames without re-running calculations |
| **Integrity** | Smoke checks that the graph (not filenames or hardcoded UI) is the source of truth |
| **Logs / Performance** | Audit events, lifecycle events, per-interaction performance traces |

---

## 2. Isolation from production

| Property | Behavior |
|----------|----------|
| Backend gate | `DEV_INSPECTION_ENABLED=1` — inspection API returns **404** when unset |
| Frontend gate | `env.devToolsAvailable` (build) + **Dev Mode** toggle (`devModeActive`, default off) — inspector UI lazy-loaded only when both are true |
| Runtime impact | Instrumentation is read-only; optional **breakpoints** only pause the executor loop between nodes |
| Electron | `DEV_INSPECTION_ENABLED=1` on every desktop backend spawn; UI visibility controlled by Dev Mode toggle |

### Environment variables

| Variable | Where | Effect |
|----------|-------|--------|
| `DEV_INSPECTION_ENABLED` | Backend | Enables inspection API and enriched executor metadata |
| `VITE_ENABLE_DEV_TOOLS` | Frontend build | Ships dev UI chunks in packaged Electron (`devToolsAvailable`) |
| Dev Mode toggle | Frontend runtime | User enables Inspector, hovers, Node Edit |
| `DEV_STUDIO_ENABLED` | Backend | Enables Node Dev Studio API (all Electron builds) |

---

## 3. Architecture

```
Task execution (executor.py)
       │
       ├── _execution_trace      (per-node results + inspection metadata)
       ├── _planner_decisions    (when inspection enabled)
       ├── _execution_events     (audit log, when inspection enabled)
       ├── _replay_snapshot      (immutable frames, when inspection enabled)
       └── _lifecycle_events     (workflow documentation events)
       │
       ▼
engine/inspection/builder.py  →  consolidated payload
       │
       ▼
GET /api/v1/tasks/{taskId}/inspection?session_id=...
       │
       ├── Desktop Developer Inspector (bottom dock panel)
```

### Backend module layout

```
engine/inspection/
  dev_guard.py          inspection_enabled()
  models.py             ExecutionTraceStep, PlannerDecision, ValueProvenanceRecord, ReplayFrame
  trace.py              Normalize trace; enrich executor metadata
  planner_decisions.py  Per-node planner explanations from ExecutionPlan
  provenance.py         Provenance index from display blocks
  replay.py             Replay frames and snapshots
  integrity.py          Four graph integrity checks
  builder.py            build_inspection_payload()
  performance_trace.py  trace_id-scoped spans (dev-only performance panel)

api/inspection.py       API helpers (get payload, breakpoints, integrity run)
api/performance_trace.py GET /api/v1/dev/performance/traces
```

### Frontend layout

Primary developer surface: **right-panel dev tabs** (`Planner`, `Task State`, `Performance`) when Dev Mode is enabled.

```
dev/desktop_ui/inspector/
  PlannerDevTab.tsx             Right panel: Planner tab entry
  PlannerDevPanel.tsx           Header card, traversal timeline, phase/requirements/warnings
  PlannerHeaderCard.tsx         Workflow, phase, active node, status badge, why_here
  PlannerTraversalTimeline.tsx  Vertical traversal path (completed/current/blocked/skipped)
  PlannerPhasePanel.tsx         Current vs future phase fields
  PlannerRequirementsPanel.tsx  Conditional, lookup, calculation requirements
  PlannerWarningsPanel.tsx      Plan validation + planner warnings
  TaskStateDevTab.tsx           Right panel: Task State tab entry
  TaskStateDevPanel.tsx         Structured facts, decisions, outputs, validation, timeline
  TaskStateHeaderCard.tsx       Task summary card
  FactsTable.tsx                Facts / inputs table
  DecisionsPanel.tsx            Branch decisions and assumptions
  OutputsPanel.tsx              Produced outputs
  ValidationPanel.tsx           Validation status and conflicts
  TraceTimelinePanel.tsx        Execution + lifecycle event timeline
  InspectorAdvancedSection.tsx  Collapsed raw JSON (Advanced / Raw Data)
  plannerInspectorSummary.ts    resolvePlannerInspectorSummary
  validateEngineeringPlan.ts    Client-side plan invariant checks (mirrors plan_validation.py)
  useInspectionPayload.ts       Poll inspection API for active task (separate inspection_poll traces)
  PerformanceDevTab.tsx           Right panel: Performance tab entry
  PerformanceTracePanel.tsx       Trace selector, span table, severity highlighting
  usePerformanceTraces.ts         Merge frontend store traces with backend poll API
  useDevRenderSpan.ts             Double-rAF dev panel render timing
  performanceTraceHelpers.ts      Duration formatting and severity thresholds

desktopApp/src/services/api/inspectionApi.ts
desktopApp/src/services/performance/tracedRequest.ts
desktopApp/src/store/performanceTraceStore.ts
desktopApp/src/types/backend/inspection.ts   PlannerInspectorSummaryDto, TaskStateViewsDto, PerformanceTraceDto
```

Legacy bottom-dock `DeveloperInspector.tsx` (execution trace) may exist but is not the primary dev surface for planner/task state.

---

## 4. Quick start

### Prerequisites

- Backend running with inspection enabled
- Desktop app in dev mode (or `npm run dev` with `VITE_DEV_MODE=true`)
- An active task with workflow execution (inputs submitted, calculation run)

### Terminal 1 — backend

From the repository root:

```powershell
set DEV_INSPECTION_ENABLED=1
python -m api.server
```

When using the Electron desktop app in development, `DEV_INSPECTION_ENABLED` is set automatically.

### Terminal 2 — desktop app

```powershell
cd desktopApp
npm run dev
```

### Using the inspector

1. Create or activate a task and run a workflow (submit inputs, execute).
2. Enable **Dev Mode** in the app header.
3. Open the **Planner** or **Task State** tab in the right panel while stepping through the workflow.
4. Use **Advanced / Raw Data** collapsed sections for canonical JSON when needed.

---

## 5. REST API

All routes return **404** when `DEV_INSPECTION_ENABLED` is not set.

### Get inspection payload

```
GET /api/v1/tasks/{taskId}/inspection?session_id={sessionId}
```

Response fields:

| Field | Description |
|-------|-------------|
| `engineering_plan` | **Canonical** normalized engineering plan (source of truth) |
| `engineering_plan_view` | Human-readable phases/overview |
| `planner_inspector_summary` | Compact planner debug rebuilt from `engineering_plan` on each fetch |
| `planner_inspector_summary.header` | Workflow, phase, active node, status badge, `why_here` (inspector debug only) |
| `planner_inspector_summary.phase_panel` | Current-phase active/completed/missing/future fields |
| `planner_inspector_summary.traversal_path` | Ordered timeline rows for traversal UI |
| `planner_inspector_summary.requirements_panel` | Unified requirement rows with resolution kind and display status |
| `inspector_summary` | Compact task-state summary |
| `canonical_task_state` | Layered canonical task state |
| `task_state_views` | UI-friendly projections: `state_summary`, `facts_view`, `decisions_view`, `outputs_view`, `validation_view`, `trace_timeline` |
| `legacy_goal_map` | Deprecated goal_store projection — debug only |
| `execution_trace` | Normalized steps: `step_index`, `node_id`, `node_type`, `status`, `duration_ms`, `selection_reason`, `inputs`, `outputs`, edges |
| `planner_decisions` | Map of `node_id` → why selected, trigger dependency, edge, rule, rejected candidates |
| `planning_summary` | Root-level planner summary from task outputs |
| `provenance_index` | All displayed values with source node, property, `generated_by`, `consumed_by` |
| `provenance_warnings` | Blocks missing provenance (dev warning) |
| `workflow_state` | Full runtime workflow state |
| `execution_events` | Persisted audit events (`EventLogger`) |
| `lifecycle_events` | Workflow documentation lifecycle events |
| `replay_frames` | Step-through frames (active node, visited, pending, variables, outputs) |
| `replay_snapshot` | Immutable snapshot stored on task completion |
| `integrity_checks` | Results of four graph integrity checks |
| `performance` | `total_duration_ms`, `by_node_ms` |
| `breakpoint` | Current pause/step state |

### Set execution breakpoint (pause / step / resume)

```
POST /api/v1/tasks/{taskId}/inspection/breakpoint?session_id={sessionId}
Content-Type: application/json

{ "paused": true }    // pause before next node
{ "step": true }      // run one more node then pause
{ "paused": false }   // resume
```

The executor checks `_inspection_breakpoint` on task outputs between nodes when inspection is enabled.

### Run integrity checks

```
GET /api/v1/tasks/{taskId}/inspection/integrity?session_id={sessionId}
```

Returns `{ "checks": [ { "check_id", "name", "passed", "message", "details" } ] }`.

### Performance traces (dev only)

```
GET /api/v1/dev/performance/traces?limit=40
```

Returns `{ "traces": [ PerformanceTraceDto, ... ] }` — recent interaction traces from the in-memory ring buffer (max 40).

Each `submit_input` / `create_task` interaction should share one `trace_id`. The **desktop app generates the trace id** and sends `X-Performance-Trace-Id` on traced requests; the backend accepts the header and only generates a fallback when missing.

| Field | Description |
|-------|-------------|
| `trace_id` | 16-char hex interaction id |
| `trigger` | `submit_input`, `create_task`, `inspection_poll`, or HTTP route label |
| `task_id` | Active task when known |
| `total_duration_ms` | Wall time for the interaction |
| `llm_call_occurred` | True when any span used the LLM client |
| `status` | `running`, `success`, or `error` |
| `spans` | Typed spans (`op_type`, `duration_ms`, `status`, `llm`, short `notes`) |
| `spans_omitted` | Count truncated when span limit (80) exceeded |

`performance_trace` is also attached to `task_state` JSON responses when inspection is enabled.

**Inspection poll separation:** `GET .../inspection` uses `trigger = "inspection_poll"`. Poll traces must not merge into `submit_input` traces. The Performance tab shows the trigger label to make this visible.

**Frontend spans** (desktop app only): `request_sent`, `response_received`, `frontend_state_update`, and dev render spans (`planner_dev_panel_render`, `task_state_dev_panel_render`, etc.) use `op_type = "frontend"`.

#### Profiling script

From the repository root:

```powershell
set DEV_INSPECTION_ENABLED=1
python scripts/profile_submit_input.py --steps 2 --inspection-poll
```

Prints per-trace op_type breakdown, top slow spans, and submit vs inspection_poll summary. Backend-only — frontend spans appear when reproducing through the desktop app Performance tab.

---

## 6. Execution trace

Each step in `execution_trace` corresponds to one node the executor visited.

**Status values:** `success`, `failed`, `skipped`, `awaiting_input`, `pending`

**Enriched metadata** (in raw `_execution_trace` under `trace.inspection` when inspection is enabled):

- `step_index`, `workflow_id`, `node_type`
- `duration_ms` (from `time.perf_counter()` around `NodeRunner.run()`)
- `incoming_edge` / `outgoing_edge` (`from_node`, `to_node`, `edge_type`)
- `selection_reason` (from planner decisions or skip reason)

Skipped planner nodes appear from `plan.skipped_nodes` via `_skipped_trace`.

---

## 7. Value provenance

Provenance is attached to display blocks at API build time (`api/node_provenance.py`) and indexed for the inspector (`engine/inspection/provenance.py`).

Each record includes:

- `source_node`, `source_property` (e.g. `outputs.value`, `display_latex`)
- `generated_by` — upstream node from graph edges
- `consumed_by` — downstream nodes
- `transformation_history` — calculation / render_steps / lookup from execution trace
- `missing: true` when no source node could be resolved (surfaced in `provenance_warnings`)

Inline dev hovers (`DevNodeTooltip`) show `generated_by` and `consumed_by` when hovering wrapped UI values.

---

## 8. Planner decisions

Per-node records are built from `ExecutionPlan` structure (`engine/inspection/planner_decisions.py`) and persisted as `_planner_decisions` when inspection is enabled.

| Field | Meaning |
|-------|---------|
| `why_selected` | e.g. `dependency_satisfied:{trigger}` or skip reason |
| `trigger_dependency` | Node that unlocked this step |
| `edge_followed` | Graph edge used |
| `rule_fired` | `topological_sort`, `when_clause`, etc. |
| `rejected_candidates` | Nodes skipped with reasons |

Select a trace step in the Inspector, then open the **Planner** tab to see the decision for that node.

### Planner tab (engineering plan)

The **Planner** dev tab is driven by **`engineering_plan`** (canonical), not the legacy `goal_store` projection. The default view is human-readable cards and tables; raw JSON is under **Advanced / Raw Data**.

| Section | Source |
|---------|--------|
| Header card | `planner_inspector_summary.header` |
| Traversal path timeline | `planner_inspector_summary.traversal_path` |
| Phase panel (current vs future) | `planner_inspector_summary.phase_panel` |
| Requirements panel | `planner_inspector_summary.requirements_panel` |
| Warnings | `planner_inspector_summary.warnings` + `validateEngineeringPlan(engineering_plan)` |
| Legacy goal map | Collapsed **Advanced / Raw Data** — `legacy_goal_map` |

`build_planner_inspector_summary()` (`engine/planner/plan_inspector.py`) includes:

- `root_goal`, `current_phase`, `next_input`, `outstanding_required_inputs`
- `current_phase_inputs`, `future_phase_inputs`
- `conditional_requirements`, `derived_or_lookup_values`, `calculations`, `system_resolved_requirements`
- `header`, `phase_panel`, `traversal_path`, `requirements_panel`
- `planner_graph_summary`, `traversal_summary`, `planner_traversal_view`, `warnings`

### Task State tab

The **Task State** dev tab renders `task_state_views` from the inspection payload (`engine/inspection/task_state_views.py`):

| Section | Source |
|---------|--------|
| State summary card | `task_state_views.state_summary` |
| Facts / inputs table | `task_state_views.facts_view` |
| Decisions and assumptions | `task_state_views.decisions_view` |
| Outputs produced | `task_state_views.outputs_view` |
| Validation and warnings | `task_state_views.validation_view` |
| Event timeline | `task_state_views.trace_timeline` |
| Raw canonical state | Collapsed **Advanced / Raw Data** |

### Planner traversal (engineering plan)

Separate from per-trace `PlannerDecision` records: the normalized **`EngineeringPlan.traversal`** field (`PlannerTraversalState`) captures how the planner is walking the workflow graph while building requirements — not the graph engine execution order.

Built in `engine/planner/planner_traversal.py` when `build_pipe_wall_engineering_plan()` runs; exposed on the task as:

| Output | Contents |
|--------|----------|
| `engineering_plan` | **Canonical** normalized plan (`plan_id`, `requirements`, `traversal`, …) — source of truth |
| `engineering_plan_view` | Human-readable phases/overview for inspector panels |
| `legacy_goal_map` | Deprecated `goal_store` projection (`GOAL-*`, `REQ-*` keys) |
| `planner_inspector_summary.traversal_summary` | Compact traversal counts |
| `planner_inspector_summary.planner_traversal_view` | Inspector panel: active node, pending expansion, branch decisions, recent events |

| Field | Meaning |
|-------|---------|
| `current_active_node_id` | Next planner traversal node (matches `input_strategy.next_fields[0]` mapped to `PARAM-*`) |
| `pending_expansion_nodes` | Known nodes blocked by unresolved gates or branch decisions (`waiting_on`, `reason`) |
| `expanded_nodes` | Nodes already expanded (e.g. workflow root) with produced requirements |
| `branch_decisions` | Unresolved/resolved path decisions with `candidate_nodes` (e.g. `pressure_loading` → `304.1.2-a`, `304.1.3`) |
| `traversal_events` | Ordered log: `node_expanded`, `node_selected`, `branch_decision_required`, `node_deferred`, … |

Open the **Planner** dev tab after starting a pipe wall thickness task. Expand **Planner traversal** for the full walk state.

Invariants: `engine/planner/plan_validation.py` (`validate_engineering_plan`, `validate_engineering_plan_dict`). Validation runs after `finalize_engineering_plan()`; failures appear in the **Warnings** section of the Planner tab.

Tests:

- `tests/planner/test_planner_traversal.py`
- `tests/planner/test_planner_inspector_views.py`
- `tests/planner/test_fresh_pipe_wall_normalized_plan.py`
- `tests/inspection/test_task_state_views.py`
- `tests/planner/test_planner_output_shape.py`
- `dev/desktop_ui/tests/validateEngineeringPlan.test.tsx`

---

## 9. Live graph visualization

### Embedded graph (Inspector Graph tab)

Nodes are colored by execution status:

| Status | Color |
|--------|-------|
| pending | grey |
| active / awaiting_input | blue |
| success | green |
| skipped | orange |
| failed | red |

### Graph panel

The inspector graph area shows workflow context alongside execution trace details in the sidebar.

---

## 10. Execution replay

Replay walks **stored frames** — it does not re-execute engineering logic by default.

- Frames built in `engine/inspection/replay.py` from trace + workflow state
- `_replay_snapshot` persisted on task completion when inspection is enabled
- Inspector **Replay** tab: step forward/back, pause/step/resume live execution via breakpoint API

Determinism is tested in `tests/acceptance/test_reproducibility.py::test_replay_frames_are_deterministic`.

---

## 11. Graph integrity checks

Four checks in `engine/inspection/integrity.py` (also exposed via API and Inspector **Integrity** tab):

| `check_id` | Validates |
|------------|-----------|
| `rename_node_id` | Nodes resolve by graph ID via `GraphStore` |
| `rename_display_title` | Titles come from node metadata, not hardcoded UI |
| `move_node_folder` | Node IDs resolve regardless of folder layout |
| `disable_node` | No dangling edges (disabled nodes would surface missing dependencies) |

These are lightweight smoke checks against the compiled graph, not full CI mutation tests.

---

## 12. Task output keys (inspection-related)

| Key | When written | Purpose |
|-----|--------------|---------|
| `_execution_trace` | Always (executor) | Raw per-node execution results |
| `_lifecycle_events` | Always (executor) | Documentation lifecycle |
| `_planner_decisions` | Inspection enabled | Per-node planner explanations |
| `_plan_edges` | Inspection enabled | Serialized plan edges |
| `_skipped_trace` | Inspection enabled | Skipped nodes for trace UI |
| `_execution_events` | Inspection enabled | Persisted `EventLogger` events |
| `_replay_snapshot` | Inspection enabled | Immutable replay frames |
| `_inspection_breakpoint` | Dev breakpoint API | Pause/step/resume state |
| `_provenance_warnings` | Inspection build | Missing provenance flags |

---

## 13. Testing

```bash
# Inspection API, trace enrichment, planner decisions, integrity
python -m pytest tests/api/test_inspection_api.py tests/api/test_performance_trace.py tests/execution/test_inspection_trace.py tests/planner/test_planner_decisions.py tests/integrity/ -q

# Replay determinism
python -m pytest tests/acceptance/test_reproducibility.py::TestReproducibilityAcceptance::test_replay_frames_are_deterministic -q

# Frontend
cd desktopApp && npm run test:run -- ../dev/desktop_ui/tests/ExecutionTracePanel.test.tsx ../dev/desktop_ui/tests/PerformanceTracePanel.test.tsx
```

---

## 14. Non-goals

- Does not modify node schema, planner algorithms, or validation rules
- Does not expose inspection UI or API in production builds
- Does not replace Node Dev Studio (authoring) — complements it

---

## 15. Related documentation

- [Node Dev Studio](node_dev_studio.md) — YAML node authoring
- [Graph platform architecture](architecture/graph_platform.md) — compile pipeline and runtime graph
- [Developer Inspection Framework spec](todo/Developer%20Inspection%20Framework.md) — original requirements document
