# Center panel output contract

User-facing engineering workspace scroll area for active tasks. Defines block roles, lifecycle, stable IDs, ordering, and layer ownership. See `docs/rules.md` §21 (Flow Guidance Layer).

## Surfaces

| Surface | Owns | Must not own |
| --- | --- | --- |
| **Scroll area** | Durable transcript + preview-tier engineering blocks | Composer questions |
| **Composer** | Short active question + control (`current_ask`) | Long narration, equations |

`PresentationBlock` is scroll/narration data only. Do not put composer prompt text on `PresentationBlock`.

## Backend authority

- **Canonical durable transcript:** `task_state.flow_guidance.transcript_blocks`, persisted in `task.outputs["flow_guidance_transcript"]` and synced via `api/flow_guidance_sync.py` (not serializers).
- **Engineering snapshot:** `task_state.display_outputs` (rebuilt each projection).
- **Current snapshot (ephemeral):** `task_state.flow_guidance.presentation_blocks` — matched guidance for this turn only; not the durable history.
- **Frontend cache:** UX smoothing only; API transcript wins on reload.

## Report vs transcript (Phase 6)

The center-panel scroll and report preview may consume the same **presentation package**:

| Package part | Role |
| --- | --- |
| `flow_guidance.transcript_blocks` | Durable display history (guidance, runtime texts, archives, completion suggestions) |
| `display_outputs` | Engineering snapshot blocks (equations, tables, traces) |
| Shared `REPORT_ROLE_ORDER` | Single ordering contract in `contracts/center_panel_report_role_order.json` |

**Engineering truth boundary:** Final report generation (`engine/reports/report_data.py`, execution trace, `ReportData`) remains the source of calculation truth, validation outcomes, and standards applicability. Transcript blocks are **display history only** — they must not replace or override engineering report data.

Assembly helpers:

- Python: `api/center_panel_contract.py` (`presentation_package_from_task_state`, `assemble_center_panel_scroll_blocks`)
- Desktop: `desktopApp/src/utils/buildCenterPanelTranscript.ts` + `centerPanelContract.ts`

Sync test: `tests/api/test_center_panel_phase6_contract.py` and `desktopApp/tests/utils/centerPanelContractSync.test.ts` both read `contracts/center_panel_report_role_order.json`.

## Lifecycle table

| `display_role` | Lifecycle | Owner |
| --- | --- | --- |
| `workflow_intro` | durable | Engineering display (runtime `texts`) — Phase 1B |
| `scope_assumption` | durable | Engineering display |
| `branch_narration` | durable | Flow Guidance Layer |
| `input_context` | durable or preview | Flow Guidance (durable when in transcript); preview when tied to `display_channel` |
| `engineering_reference` | durable | Engineering display — Phase 3 |
| `paragraph_context` | durable | Engineering display (live focus paragraph) |
| `equation_preview` | preview | Engineering display (`display_outputs`) — legacy ids only |
| `ask_archive` | durable (transcript only) | Messaging + `api/input_archive_transcript.py` — Phase 2; **not shown in center-panel scroll** |
| `answer_archive` | durable (transcript only) | Messaging + `api/input_archive_transcript.py` — Phase 2; **not shown in center-panel scroll** |
| `calculation_trace` | durable | Execution + display |
| `validation_check` | durable | Engineering display |
| `result_summary` | durable | Engineering display / runtime `texts` — Phase 1B |
| `recommendation` | durable | Engineering display |
| `next_workflows` | durable | Workflow runtime `suggested_workflows` — Phase 5 |

## Stable `block_id` rules

**Guidance YAML `entries[].id` values must be unique within each workflow file.**

| Role | Pattern |
| --- | --- |
| `branch_narration` / `input_context` (guidance) | `guidance-{workflow_id}-{entry_id}` |
| `workflow_intro` | `workflow-intro-{workflow_id}` |
| `scope_assumption` | `scope-assumption-{source_node_id}` |
| `equation_preview` | legacy preview ids (`path-preview-equation-*`) — **deprecated** |
| `calculation_trace` | `equation-{equation_node_id}` (stable across preview and evaluated states) |
| `paragraph_context` | `paragraph-{node_id}` (live focus paragraph with `presentation.summary`) |
| `engineering_reference` | `paragraph-{node_id}` (trace/reference prose) |
| `recommendation` (lookup table) | `table-lookup-{node_id}` |
| `validation_check` | `validation-{semantic_key}` (e.g. `validation-thin-wall-criterion`) |
| `result_summary` | `result-summary-{workflow_slug}` |
| `ask_archive` | `archived-ask-{parameter_id}-{submission_id}` (transcript storage only; excluded from center-panel scroll) |
| `answer_archive` | `archived-answer-{parameter_id}-{submission_id}` (transcript storage only; excluded from center-panel scroll) |
| `next_workflows` | `next-workflows-{task_id}-{workflow_id}` |

Future: `guidance-{workflow_id}-{entry_id}-{activation_key}` when entry reuse is required.

`workflow_id` in ids uses normalized slug: lowercase, hyphens → underscores.

## Same `block_id` update behavior

1. Same `block_id` = same logical block.
2. **Before task completion:** update existing block in place when content/metadata changes.
3. **After task completion:** preserve transcript (no in-place updates unless workflow recalculated).
4. Never render two visible blocks with the same `block_id`.

## Default report order

1. `workflow_intro`
2. `scope_assumption`
3. `branch_narration`
4. `ask_archive` / `answer_archive` (transcript only; excluded from scroll)
5. `engineering_reference`
6. `paragraph_context`
7. `input_context`
8. `calculation_trace`
9. `equation_preview`
10. `validation_check`
11. `result_summary`
12. `recommendation`
13. `next_workflows`

**Center-panel scroll exclusion:** `ask_archive` and `answer_archive` remain in `flow_guidance.transcript_blocks` for audit/history but are **not** merged into `ordered_scroll_blocks` or the desktop center-panel transcript. Users answer via the composer (`current_ask`), not the scroll area.

Persisted archives may still exist in backend transcript storage; frontend filters repair older sessions via `buildCenterPanelTranscript.ts` and `flowGuidanceTranscript.ts`.

Within the same role: chronological append order. Preview-tier (non-equation): replace prior block in the same `display_channel`. Equation blocks merge **by stable `block_id` only** — never by `display_channel`.

## Generic display block contracts

`build_display_outputs()` (`api/output_blocks.py`) is workflow-agnostic. Block ids derive from `node_id`, `equation_node_id`, or trace keys — never from workflow slug.

### Finalize pipeline (`_finalize_display_blocks`)

1. Provenance enrich (`enrich_display_blocks_provenance`, row `value_provenance`)
2. Reference dedupe (`select_primary_reference_chip` per cell)
3. Block id dedupe (`dedupe_blocks_by_id_prefer_richer` — collapse legacy preview/trace ids)
4. Role/order normalization (`sort_blocks_by_report_role` at API boundary)

`append_equation_trace_blocks` is **not** called on the live central-panel path.

### Paragraph / paragraph context

- **`paragraph_context`:** live focus paragraph when `presentation.summary` exists (`api/paragraph_display.paragraph_context_blocks_for_focus()`).
- **`engineering_reference`:** paragraph trace/reference prose from execution trace.
- **Shape:** `id=paragraph-{node_id}`, `type=text`.

### Equation preview / calculation trace

- **Stable id:** `equation-{equation_node_id}` — same block updates in place: symbolic → input table → substitution/result via `equation_display_trace`.
- **Lifecycle:** `durable` — frontend `mergeDisplayOutputs` retains prior equations when focus advances.
- **Legacy ids** (`path-preview-equation-*`, `equation-trace-*`) stripped during finalize dedupe.
- **Row provenance:** at most one primary `reference_chips` entry per cell (`api/reference_links.select_primary_reference_chip`).

### Lookup / recommendation table

- **Source:** `_execution_trace[].trace.lookup` written by execution (e.g. B36.10 schedule list on completion).
- **Shape:** `id=table-lookup-{node_id}`, `type=table`, optional `highlight_row`, `summary_text`.
- Display **must not** query standards tables at serialize time.

### Validation check

- **Source:** `task.warnings` or trace-derived checks (e.g. thin-wall criterion from `task.outputs.thin_wall` + calculation trace).
- **Shape:** `id=validation-{semantic_key}`, `type=text`, `display_role=validation_check`.

### Workflow results

- **Shape:** `id=result-summary-{workflow_slug}`, `type=text`, `display_role=result_summary`.
- **Payload:** structured deterministic summary from `api/result_summary_display.py` (`primary_result`, `applied_conditions`, `warnings`, optional `runtime_narration`).
- Loose `result-{output_key}` typed blocks are **not** emitted on the scroll path.

Legacy ids removed from builders: `minimum-thickness-equation`, `pipe-schedule-recommendation`, `path-calculation-substituted-equation`, `thin-wall-applicability-check`, `path-preview-equation-*`, `equation-trace-*`.

## Reference chips (Phase 3)

- `reference_chips` are **projected on API responses only** (serializer read path).
- They are **not** persisted in `task.outputs["flow_guidance_transcript"]` or other durable stores.
- Authoritative pointers remain `refs` on guidance blocks and legacy `reference_links` on display outputs until fully migrated.

## Equation row provenance (Phase 4)

- `value_provenance` is attached to equation `input_table.rows` inside `display_outputs` (preview-tier engineering blocks).
- It is **not** a durable transcript block type; no `calculation_trace` or `engineering_reference` persistence in Phase 4.
- `reference_chips` nested under `value_provenance` are **API projection only** (same read path as Phase 3).
- Legacy `value_reference` remains during migration; frontend prefers `value_provenance`.
- Single-hop provenance only (`source_type`: `user_input`, `equation_output`, `table_lookup`, …).

## Completion next workflows (Phase 5)

- `next_workflows` blocks append to `flow_guidance_transcript` **once** when a task reaches `COMPLETED`.
- Source: `workflows/*/runtime.yaml` `suggested_workflows`, resolved through `workflow_catalog` metadata only.
- Not used by planner, graph, execution, validation, or parameter resolution — scroll display history only.
- `block_id`: `next-workflows-{task_id}-{workflow_id}` (normalized slugs).
- API `flow_guidance.transcript_blocks` flattens `suggestions` to top level; stored form uses `PresentationBlock.payload`.

## Forbidden in normal user output

- Raw planner JSON, `engineering_plan`, `legacy_goal_map`, internal node ids as primary visible text.
- `waiting_user_input` as a displayed value in completed calculation tables.

## Phase 1A scope

Render existing flow guidance into `flow_guidance.transcript_blocks` (backend-persisted) and center panel scroll. No `center_panel_transcript` field. No initiation/result runtime texts, composer shortening, references, archives, or completion workflows.
