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

### Projection terminology

`task_state.flow_guidance` and `task_state.display_outputs` are **serialized API projections** for display. They are authoritative for **what to render** on reload, not for engineering navigation or calculations.

| Concern | Authority |
| --- | --- |
| Navigation ordering / missing fields | `engineering_plan`, planner outputs |
| Parameter prompt copy | `current_ask`, `engine/messaging/`, PARAM nodes |
| Equation engineering truth | Execution trace, `equation_display_trace` (`docs/rules.md` §24) |
| Durable display history | `flow_guidance.transcript_blocks`, durable `display_outputs` equation blocks (§25) |

`flow_guidance.presentation_blocks` is an ephemeral projection snapshot — not workflow engineering state.

### Implementation drift (code alignment deferred to Phase 2B)

| Topic | Target (this contract) | Drift (do not document as permanent) |
| --- | --- | --- |
| Active user ask | Composer (`current_ask` / `active_prompt`) only; scroll must not own composer questions | `api/output_blocks._input_waiting_blocks()` may emit volatile `input_waiting` in `display_outputs` — migration decision in Phase 2B |
| Workflow introduction | Single durable `workflow_intro` (`workflow-intro-{workflow_id}`) | Some API/tests still reference separate `title` display role — migration decision in Phase 2B |

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
- Desktop: `desktopApp/src/utils/buildCenterPanelTranscript.ts` + `displayRole.ts`

Sync test: `tests/models/test_display_role_contract.py` and `desktopApp/tests/utils/centerPanelContractSync.test.ts` both read `contracts/center_panel_report_role_order.json`.

## Canonical display roles (`models/display_role.py`)

Authority module: `DisplayRole`, `DisplayState`, `EquationContent`, `DISPLAY_ROLE_ORDER`, `resolve_display_block()`.

| Field | Answers | Values |
| --- | --- | --- |
| `display_role` | What function does this block serve in the transcript? | `equation`, `node_intro`, `result_summary`, … |
| `display_state` | What presentation stage is this **equation** block in? | `preview`, `active`, `evaluated` |
| `equation_content` | What equation content is shown? | `symbolic`, `substituted`, `evaluated` |
| `lifecycle` | Ephemeral vs durable merge semantics | `preview`, `durable`, `volatile` |
| `display_channel` | Preview-tier replacement channel | `current_equation_preview`, `current_node_intro` |
| `result_kind` | Result semantic type | `workflow`, `calculation`, `recommendation` |

**Reserved:** `scope_assumption` is an ordering slot only (no builder emits it yet).

**Not enum members (legacy — migrate only):** `node_activation`, `equation_preview`, `equation_trace`, `preview`, `activation`, `intro`, `recommendation`, `calculation_trace`, `validation_check`, `substituted`, `derived`, `conclusion`, `result`.

Legacy migration lives only in `tests/helpers/legacy_display_role_migration.py` and `scripts/migrate_persisted_display_roles.py`. Production code validates and infers — no runtime alias maps.

## Lifecycle table

| `display_role` | Lifecycle | Owner |
| --- | --- | --- |
| `workflow_intro` | durable | Engineering display (runtime `texts`) |
| `scope_assumption` | durable | **Reserved** ordering slot |
| `branch_narration` | durable | Flow Guidance Layer |
| `input_context` | durable or preview | Flow Guidance (durable when in transcript); preview when tied to `display_channel` |
| `engineering_reference` | durable | Engineering display |
| `paragraph_context` | durable | Engineering display (live focus paragraph) |
| `node_intro` | preview | Engineering display (`path-preview-intro-*`) |
| `equation` | preview or durable | Engineering display — see `display_state` |
| `applicability` | durable | Engineering display |
| `warning` | durable | Engineering display |
| `result_summary` | durable | Engineering display / runtime `texts` (`result_kind: workflow`) |
| `lookup_table_recommendation` | durable | Engineering display |
| `ask_archive` | durable (transcript only) | Messaging — **not shown in center-panel scroll** |
| `answer_archive` | durable (transcript only) | Messaging — **not shown in center-panel scroll** |
| `next_workflows` | durable | Workflow runtime `suggested_workflows` |

### Equation blocks (`display_role: equation`)

| `display_state` | Lifecycle | Typical ids |
| --- | --- | --- |
| `preview` | preview | `path-preview-equation-*`, stable `equation-{id}` before evaluation |
| `active` | preview | `node-activation-equation-*` |
| `evaluated` | durable | stable `equation-{equation_node_id}` |

Dedupe: preview-tier blocks with the same `equation_node_id` collapse to the richest payload; `active` drops when `preview` exists. Durable blocks update in place by stable `equation-{equation_node_id}` id.

## Stable `block_id` rules

**Guidance YAML `entries[].id` values must be unique within each workflow file.**

| Role | Pattern |
| --- | --- |
| `branch_narration` / `input_context` (guidance) | `guidance-{workflow_id}-{entry_id}` |
| `workflow_intro` | `workflow-intro-{workflow_id}` |
| `scope_assumption` | `scope-assumption-{source_node_id}` |
| `node_intro` | `path-preview-intro-{node_id}` |
| `equation` (stable) | `equation-{equation_node_id}` |
| `equation` (preview/active legacy ids) | `path-preview-equation-*`, `node-activation-equation-*` |
| `paragraph_context` | `paragraph-{node_id}` (live focus paragraph with `presentation.summary`) |
| `engineering_reference` | `paragraph-{node_id}` (trace/reference prose) |
| `lookup_table_recommendation` | `table-lookup-{node_id}` |
| `applicability` | `validation-{semantic_key}` (e.g. `validation-thin-wall-criterion`) |
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

Authoritative tuple: `models/display_role.DISPLAY_ROLE_ORDER` → `contracts/center_panel_report_role_order.json`.

1. `workflow_intro`
2. `scope_assumption` (reserved)
3. `branch_narration`
4. `ask_archive` / `answer_archive` (transcript only; excluded from scroll)
5. `engineering_reference`
6. `paragraph_context`
7. `input_context`
8. `node_intro`
9. `equation` (single slot — sort by stable id, then `display_state`)
10. `applicability`
11. `warning`
12. `result_summary`
13. `lookup_table_recommendation`
14. `next_workflows`

**Center-panel scroll exclusion:** `ask_archive` and `answer_archive` remain in `flow_guidance.transcript_blocks` for audit/history but are **not** merged into `ordered_scroll_blocks` or the desktop center-panel transcript. Users answer via the composer (`current_ask`), not the scroll area.

Persisted archives may still exist in backend transcript storage; frontend filters repair older sessions via `buildCenterPanelTranscript.ts` and `flowGuidanceTranscript.ts`.

Within the same role: chronological append order. Preview-tier (non-equation): replace prior block in the same `display_channel`. Equation blocks merge **by stable `block_id` only** — never by `display_channel`.

## Generic display block contracts

`build_display_outputs()` (`api/output_blocks.py`) is workflow-agnostic. Block ids derive from `node_id`, `equation_node_id`, or trace keys — never from workflow slug.

### Finalize pipeline (`_finalize_display_blocks`)

1. Provenance enrich (`enrich_display_blocks_provenance`, row `value_provenance`)
2. Reference dedupe (`select_primary_reference_chip` per cell)
3. Block id dedupe (`dedupe_blocks_by_id_prefer_richer`)
4. `resolve_display_block()` on each block (validate + infer; strip `internal_display_role`)
5. Role/order normalization (`sort_blocks_by_report_role` at API boundary)

`append_equation_trace_blocks` is **not** called on the live central-panel path.

### Paragraph / paragraph context

- **`paragraph_context`:** live focus paragraph when `presentation.summary` exists (`api/paragraph_display.paragraph_context_blocks_for_focus()`).
- **`engineering_reference`:** paragraph trace/reference prose from execution trace.
- **Shape:** `id=paragraph-{node_id}`, `type=text`.

### Equation blocks

- **Canonical:** `display_role: equation` + `display_state` + `equation_content`.
- **Stable id:** `equation-{equation_node_id}` — same block updates in place: symbolic → input table → substitution/result via `equation_display_trace`.
- **Lifecycle:** `display_state` in `{preview, active}` → `preview`; `evaluated` → `durable`.
- **Center-panel live snapshot:** `mergeDisplayOutputs` includes preview/active equations from the **current API response** so the scroll area shows the in-progress equation and parameter table. Session transcript cache (`transcriptCache`) stores **durable blocks only** — preview equations are not persisted across reload.
- **Progressive layout (single block):** symbolic line → input table → substituted line (when all inputs resolved) → evaluated result line. Parameter table remains visible after evaluation.
- **Legacy ids** (`path-preview-equation-*`, `equation-trace-*`) may still appear on ids but roles are canonical only in API output.
- **Row provenance:** at most one primary `reference_chips` entry per cell (`api/reference_links.select_primary_reference_chip`).
- **Persisted trace keys:** `_equation_trace_keys` suffix `|equation` (migrate legacy `|equation_trace` via `scripts/migrate_persisted_display_roles.py`).

### Lookup / recommendation table

- **Source:** `_execution_trace[].trace.lookup` written by execution (e.g. B36.10 schedule list on completion).
- **Shape:** `id=table-lookup-{node_id}`, `type=table`, optional `highlight_row`, `summary_text`.
- Display **must not** query standards tables at serialize time.

### Validation check

- **Source:** `task.warnings` or trace-derived checks (e.g. thin-wall criterion from `task.outputs.thin_wall` + calculation trace).
- **Shape:** `id=validation-{semantic_key}`, `type=text`, `display_role=applicability`.

### Workflow results

- **Shape:** `id=result-summary-{workflow_slug}`, `type=text`, `display_role=result_summary`, `result_kind=workflow`.
- **Payload:** structured deterministic summary from `api/result_summary_display.py` (`primary_result`, `applied_conditions`, `warnings`, optional `runtime_narration`).
- Loose `result-{output_key}` typed blocks are **not** emitted on the scroll path.

Legacy ids removed from builders: `minimum-thickness-equation`, `pipe-schedule-recommendation`, `path-calculation-substituted-equation`, `thin-wall-applicability-check`, `path-preview-equation-*`, `equation-trace-*`.

## Reference chips (Phase 3)

- `reference_chips` are **projected on API responses only** (serializer read path).
- They are **not** persisted in `task.outputs["flow_guidance_transcript"]` or other durable stores.
- Authoritative pointers remain `refs` on guidance blocks and legacy `reference_links` on display outputs until fully migrated.

## Equation row provenance (Phase 4)

- `value_provenance` is attached to equation `input_table.rows` inside `display_outputs` (preview-tier engineering blocks).
- It is **not** a durable transcript block type.
- `reference_chips` nested under `value_provenance` are **API projection only** (same read path as Phase 3).
- Legacy `value_reference` remains during migration; frontend prefers `value_provenance`.
- Single-hop provenance only (`source_type`: `user_input`, `equation_output`, `table_lookup`, …).

## Completion next workflows (Phase 5)

- `next_workflows` blocks append to `flow_guidance_transcript` **once** when a task reaches `COMPLETED`.
- Source: workflow nested `runtime.suggested_workflows` on primary workflow YAML, resolved through `workflow_catalog` metadata only.
- Not used by planner, graph, execution, validation, or parameter resolution — scroll display history only.
- `block_id`: `next-workflows-{task_id}-{workflow_id}` (normalized slugs).
- API `flow_guidance.transcript_blocks` flattens `suggestions` to top level; stored form uses `PresentationBlock.payload`.

## Forbidden in normal user output

- Raw planner JSON, `engineering_plan`, `legacy_goal_map`, internal node ids as primary visible text.
- `waiting_user_input` as a displayed value in completed calculation tables.

## Phase 1A scope (historical)

Phase 1A originally scoped transcript-only guidance. Current contract also includes archives, completion suggestions, reference chips, and `display_outputs` merge (Phases 3–6) as documented above.
