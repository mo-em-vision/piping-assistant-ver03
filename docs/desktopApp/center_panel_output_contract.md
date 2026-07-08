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
| `equation_preview` | preview | Engineering display (`display_outputs`) |
| `ask_archive` | durable | Messaging + `api/input_archive_transcript.py` — Phase 2 |
| `answer_archive` | durable | Messaging + `api/input_archive_transcript.py` — Phase 2 |
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
| `equation_preview` | existing preview ids (`path-preview-equation-*`, etc.) |
| `calculation_trace` | `equation-trace-{semantic_key}` |
| `ask_archive` | `archived-ask-{parameter_id}-{submission_id}` |
| `answer_archive` | `archived-answer-{parameter_id}-{submission_id}` |
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
4. `ask_archive`
5. `answer_archive`
6. `engineering_reference`
7. `input_context`
8. `equation_preview`
9. `calculation_trace`
10. `validation_check`
11. `result_summary`
12. `recommendation`
13. `next_workflows`

Within the same role: chronological append order. Preview-tier: replace prior block in the same `display_channel`.

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
