# engine/inspection/

Developer inspection framework: execution trace, replay, provenance, planner decisions, graph integrity. **Dev-only** (gated).

## Purpose

Debug active tasks without affecting production behavior. Enabled when `inspection_enabled()` is true (`DEV_INSPECTION_ENABLED=1` or unpackaged Electron dev).

## Entry Points

| Symbol | File |
|--------|------|
| `inspection_enabled` | `dev_guard.py` |
| `build_inspection_payload` | `builder.py` (lazy via `inspection/__init__.py`) |
| `build_execution_trace` | `trace.py` |
| `run_integrity_checks` | `integrity.py` |

## Dependencies

**Depends on:** `engine/reference/`, `engine/state/workflow_state`, `api/json_encoding`, `models` via dict serialization

**Used by:** `api/inspection.py`, `engine/executor/executor.py` (trace enrichment), `tests/execution/`, `tests/integrity/`

## Runtime Usage

**Conditional.** Production release builds typically have inspection disabled. Executor still calls trace helpers when enabled.

## Possible Dead Code

None at package level. All modules are referenced from `builder.py` or `api/inspection.py`.

## Notes

- `builder.py` imports from `api/` — coupling from engine → api (unusual boundary).
- Integrity checks are static graph/reader checks, not runtime execution validation.

## Execution Traces

```
Desktop Inspector button
  → api/inspection.py (dev_guard check)
  → build_inspection_payload(task, manager, reader)
    → planner_debug_projection.planner_debug_projection_for_task
    → plan_inspector.planner_inspector_summary_for_task
    → trace.build_execution_trace
    → replay.build_replay_frames / build_replay_snapshot
    → provenance.build_provenance_index
    → planner_decisions.planner_decisions_from_task_outputs
    → integrity.run_integrity_checks
    → workflow_state.build_workflow_state
```

```
Executor.execute_plan (when inspection enabled)
  → trace.enrich_execution_result_trace
  → trace.persist_plan_metadata
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Lazy `build_inspection_payload` | `inspection_enabled` | external |
| `builder.py` | **Assemble API payload** | `build_inspection_payload` | api/inspection |
| `value_classification.py` | Route values to inspector surfaces | `classify_inspection_value`, `INSPECTION_EXCLUDED_OUTPUT_KEYS` | task_state_views |
| `dev_guard.py` | Env gate | `inspection_enabled` | api, executor |
| `integrity.py` | Graph integrity checks | `run_integrity_checks` | builder, api |
| `models.py` | DTOs | `ExecutionTraceStep`, `PlannerDecision`, … | all inspection modules |
| `planner_decisions.py` | Plan → decision records | `build_planner_decisions` | trace, builder, api |
| `provenance.py` | Value provenance index | `build_provenance_index` | builder |
| `replay.py` | Step replay frames | `build_replay_snapshot` | builder, api |
| `trace.py` | Execution trace from outputs | `build_execution_trace`, `persist_plan_metadata` | builder, executor, api |
| `performance_trace.py` | Dev performance spans | `begin_interaction_trace`, `perf_span`, `recent_traces_snapshot` | api/server, api/desktop_service |

## Performance tracing (dev)

`performance_trace.py` groups typed spans under a client- or server-generated `trace_id` per interaction. Spans are capped (80/trace, 40 recent traces). Inspection GET routes use `trigger = "inspection_poll"` so poll cost stays separate from `submit_input`.

Profile locally:

```powershell
set DEV_INSPECTION_ENABLED=1
python scripts/profile_submit_input.py --steps 2 --inspection-poll
```
