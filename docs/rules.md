# Engineering Desktop — Agent and Implementation Rules

Source of truth for Cursor agents and contributors. `.cursor/rules/agent-rules.mdc` points here; do not contradict this file.

`docs/rules.md`, `.cursor/rules/**`, node templates, and architecture decision documents are protected files. Agents must not modify them unless the approved task explicitly lists them as allowed files. When a conflict is found, report it and propose an amendment instead of editing the rule.

---

## 1. Read before you write

Inspect target files, related tests, and existing patterns before editing. For product behavior, read the matching doc under `docs/desktopApp/` or `docs/core/` first.

---

## 2. Think before you code

State assumptions and tradeoffs. Ask when requirements, API contracts, or architecture boundaries are unclear.

---

## 3. Simplicity

Minimum code for the current problem. No premature abstraction or dependencies without clear need.

---

## 4. Surgical changes

Smallest justified diff. Match existing naming, types, and style. Avoid drive-by refactors and unrelated renames.

---

## 5. Verifications

Prove fixes with tests that exercise real behavior — not code inspection alone.

| Stage | When | Action |
| --- | --- | --- |
| **1. Targeted** | Every change | Run tests that cover the changed behavior first (new or existing). |
| **2. Subsystem** | Before completing the task | Run the relevant subsystem suite (e.g. `tests/api/…`, `tests/planner/…`, `tests/presentation/…`, `desktopApp` unit tests for the touched area). |
| **3. Smoke** | Cross-layer or user-visible workflow changes | Run MVP/release smoke when relevant: `python -m pytest tests/mvp/test_desktop_mvp_workflow.py`; `cd desktopApp && npm run verify:mvp` or `verify:release` when desktop behavior changed. |

**Report** every required test command that was not run and why. **Never** claim verification based only on reading code.

---

## 6. Goal-driven execution

Define success criteria and a short plan for non-trivial work before coding.

Every feature plan must include an **Architecture Consistency Review** (§23; status CLEAR / NEEDS_DOC_UPDATE / NEEDS_DECISION / BLOCKED) and a **Plan Review Gate** (§22). Cursor may assign **READY_FOR_REVIEW**, **REVISE**, or **BLOCKED** — not **APPROVED**. Do not implement until the consistency review is **CLEAR**, the project owner grants **APPROVED**, and the user gives an explicit implementation instruction. See **§22**, **§23**, and [`docs/process/plan_review_gate.md`](process/plan_review_gate.md).

---

## 7. Debugging

Reproduce, read the full error, change one thing at a time. Do not guess at fixes.

---

## 8. Dependencies

Prefer stdlib and existing project modules. Justify new packages.

---

## 9. Communication

Explain what changed and why. Flag uncertainty precisely.

---

## 10. Common failure modes

Stop if you drift into kitchen-sink refactors, wrong abstractions, or duplicating engineering logic in the frontend.

---

## 11. Node structure

- Workflows start from root nodes only; graph traversal reads node data.
- Use node authoring contracts under `audits/contracts/nodes/` (start at [`audits/contracts/nodes/00-START-HERE.md`](../audits/contracts/nodes/00-START-HERE.md)). Validators in `engine/validation/` remain the enforcement authority.
- Confirm template or relationship-schema changes with the user.
- Paragraph subsection naming: `.cursor/rules/paragraph-subsection-naming.mdc`.

---

## 12. User-facing prompts (planner vs messaging)

**The planner decides what to ask next; it does not own prompt copy.**

| Layer | Owns | Does not own |
| --- | --- | --- |
| **Planner** (`engine/planner/`) | Navigation phases, missing-field order, submittable parameter ids, goal tree structure | User-facing question strings, autocomplete labels, material search hints |
| **Messaging** (`engine/messaging/`) | Deterministic prompt text and resolution order (assembly only) | Which parameter is active, phase gating, graph execution |

### Where prompt text lives

- **Workflow interaction specs** — `interactions` on workflow sidecars / `runtime.yaml`. Gate phases (yes/no, branch decisions) delegate numbered formatting to `engine/messaging/step_prompt.py`.
- **PARAM-* node metadata** — `question`, `description`, `metadata.short_question`, `metadata.input_examples`, and `metadata.composer_options` labels on parameter nodes, read via `engine/messaging/parameter_prompt_context.py` (messaging-owned; Graph Engine does not own user-facing wording).
- **Equation / lookup context** — `engine/messaging/formula_parameter_prompt.py` (graph-driven; no workflow-specific branches).
- **Final messaging fallback** — structured minimal prompt from PARAM `name` / `canonical_symbol` when no higher-priority source applies.
- **LLM agent stubs** — `ai/prompts/` (intent/planner agents only; not desktop parameter asks).

### Resolution entry point

All desktop/API parameter asks must resolve through:

`engine/messaging/parameter_input_prompt.build_parameter_input_prompt()`

Order inside that function (do not bypass or reorder without updating docs and tests):

1. Workflow interaction spec / `runtime.yaml` / sidecar interaction question (gate phases use numbered formatting from `step_prompt` helpers; PARAM `question` preferred for numbered decision copy)
2. PARAM-* node `question`, then useful `description` if no question (`parameter_prompt_context.py`)
3. Equation or lookup context (`formula_parameter_prompt.guidance_for_parameter_input`)
4. Legacy `phase_questions` on planning (backward compatibility only)
5. Final messaging fallback from PARAM metadata (`name`, `symbol`, `input_examples`)

### Desktop / API prompt paths

- **Desktop workflow composer** — `task_state.current_ask.short_prompt` is the composer question (from `build_short_parameter_input_prompt()` / PARAM `metadata.short_question`). `task_state.current_ask.prompt` is the full messaging prompt from `build_parameter_input_prompt()` (guidance, formula context, numbered gate copy). `parameter.guidance` mirrors the full prompt path.
- **Chat / API presentation** — `task_state.flow_guidance.active_prompt` from `ResponseComposer` supplies the current ask block for multi-block formula or step prompts. The composer merges messaging output; it does not author prompt copy.
- **Transcript history** — `transcript_blocks` are append-only display history (§21, §25). Prior prompts remain in transcript; they are not re-resolved from `active_prompt`. Composer prompts do not belong inside equation scroll blocks.

### Do not

- Add or edit user-facing parameter prompt strings in `engine/planner/planner.py`, `goal_migration.py`, serializers, or `engine/graph/` as the **source of truth**.
- Add prompt-building logic to `engine/graph/graph_timeline.py` or other Graph Engine modules.
- Store new prompt copy in `NavigationPlan.questions` / `phase_questions` for greenfield features — resolve at display time via the messaging layer.
- Duplicate prompt catalogs in the frontend; the backend owns engineering wording.

### Design references

- `docs/core/11. planner_layer_design.md` — planner boundaries
- `docs/core/5. workflow_design.md` — phased input collection and deterministic prompts
- `engine/messaging/README.md` — messaging module inventory

---

## 13. Graph-driven workflow paths (no hardcoded steps)

**Workflow paths, branches, and parameter asks must come from graph expansion — not from hardcoded lists in engine, API, or UI code.**

The active execution subgraph is resolved from authored knowledge nodes: `assumptions`, `applicability.applies_when`, edge `when` clauses, `depends_on`, `interactions`, parameter `resolution`, and workflow `entry_points`. When the user supplies or changes a fact, replanning must shrink or grow the goal tree and missing-field set to match the newly active path.

### Source of truth (priority)

1. **Node metadata** — `assumptions`, execution-sidecar `applicability`, `interactions`, `provisional_assumptions`, parameter `resolution`.
2. **Typed edges** — `depends_on`, `requires_parameter`, `introduces_parameter`, etc., including `when` metadata on the edge.
3. **Workflow runtime sidecar** — `workflows/<id>/runtime.yaml`: `interactions`, `assumption_gate_fields`, and **phase labels/order only** (not a static list of all parameters for every branch).
4. **Engine expansion policy** — `engine/graph/expansion_policy.py`, `lazy_expander.py`, `assumption_checker.py`, `micro_graph_engine.required_user_inputs()`.

### Engine and API must

- Derive **which nodes are active** from `expand_workflow()` / `GraphEngine.build_plan()` and edge `when` evaluation.
- Derive **which parameters to ask** from active compiled `PARAM-*` nodes on the expanded path (`required_user_inputs()`), plus execution-assumption evaluation — not from a fixed per-workflow field list.
- **Replan after each confirmed input** so branch-specific parameters (e.g. external design pressure) disappear when that branch is ruled out.
- Use navigation config **only** for phase ordering and gate-phase fields, never to inject path-specific parameters that the graph did not expand.

### Do not

- Hardcode paragraph ids, branch ids, or task field names in planner, serializers, `workflow_timeline.py`, or `workflow_bootstrap.py` to select execution paths.
- List all branch parameters unconditionally in `runtime.yaml` `navigation.phases.parameter_gathering`.
- Merge static navigation phase lists over graph-derived `required_user_inputs` (gate phases only).
- Encode workflow branching in TypeScript or `if workflow == "pipe_wall_…"` blocks in the backend.

### Where to author a new branch or gate

| Need | Author on |
| --- | --- |
| Block expansion until user confirms | Node `assumptions` with `required_for_expansion` |
| Internal vs external (or similar) branch | Edge `when` on `depends_on`, or `applicability.applies_when` on branch paragraph/equation |
| Branch-only parameter | `introduces_parameter` on the branch paragraph + parameter node; optional `applies_when` |
| Workflow-level decision before expansion | Workflow `interactions` / `assumption_gate_fields` in `runtime.yaml` |
| Ask order within a phase | `navigation.phases` order in `runtime.yaml` (fields must still be graph-active) |

After graph YAML changes: `python scripts/build_graph_db.py` when using SQLite cache; extend `tests/graph/test_expansion_policy.py` (assert via metadata behavior, not engine id literals).

### Allowed non-graph configuration

- **Presentation order** — timeline sort keys and composer row order (filtered to graph-revealed fields via `graph_input_order` / `collection_field_order` on task outputs).
- **Prompt copy** — `engine/messaging/` and workflow `interactions[].question` (see §12).
- **Phase enum labels** — `expansion_assumptions`, `path_decisions`, `parameter_gathering`, etc.

Full rule file: `.cursor/rules/graph-expansion.mdc`. Design detail: `docs/core/14. graph_engine_design.md`, `docs/desktopApp/05_backend_ui_contract.md` §6.

---

## 14. Parameter key consistency (lookup tables and databases)

**Runtime parameter keys must match the `key` field on the global `PARAM-*` node and the `inputs[].id` on any lookup table that consumes that parameter.**

| Layer | Use |
| --- | --- |
| `PARAM-*` node | `key: material_grade` (machine-safe, stable) |
| Lookup table YAML | `inputs[].id: material_grade` when bound to `PARAM-material-grade` |
| Workflow `runtime.yaml` | Same key when the parameter legitimately appears in gate or ordering metadata (`assumption_gate_fields`, `navigation.phases` gate fields) — not as a substitute for graph expansion (§13) |
| Facts / API submit | Store under canonical `key` (`material_grade`) |
| Material catalog | `material_id` is a catalog token (e.g. `astm_a106_gr_b`), not the parameter key |

Do **not** introduce shortened or legacy keys (`material`) in new YAML. Legacy aliases are accepted only when **reading** old facts (`engine/reference/parameter_keys.py`).

---

## 15. Derived parameter value display (equation input tables)

**When a parameter value is not yet in task state but is produced by another graph node, show a standards reference link in the Value column — not "Awaiting user input".**

| Parameter source | Graph signal | Value column when unresolved |
| --- | --- | --- |
| Equation output | `parameter_class: calculated_quantity` or incoming `calculates_parameter` | Link to governing paragraph (e.g. §304.1.2 for `t` from eq. 3a) |
| Table lookup | `resolution.method: table_lookup` or incoming `returns_parameter` from a lookup node | Link to the lookup/table paragraph |
| User input | `resolution.method: user_input` (default) | `Awaiting user input` until a fact is confirmed |

### Resolution

- Backend: `engine/reference/parameter_value_source.py` — `resolve_parameter_value_reference()` / `resolve_input_value_reference()`.
- API equation rows: `api/equation_evaluation_display.py`, `api/equation_inputs_display.py` attach `value_reference` (`node_id`, `label`, `paragraph`) when no display value exists.
- Frontend: `EquationOutput` renders provenance with `InlineCitationText` — prefix text plus an inline hyperlink for the citation (center panel, right panel, chat use the same pattern).

### Inline prose reference links

Standard references must be **clickable inside the sentence** that cites them — not as detached chip buttons or a separate `"Standard reference"` control beside plain text.

| Rule | Requirement |
| --- | --- |
| Composition | Prefix text stays plain (`Resolved from`, `Defined in`, `Source:`); only the citation span is linked |
| Label | Full standard path (e.g. `ASME B31.3 Table A-1`, `ASME B31.3 §304.1.2`) — not short `Table A-1` alone or generic `"Standard reference"` when resolvable |
| Visual | Inline hyperlink style (underlined, no chip icon/chrome) in center panel, right panel, and chat |
| Backend | `value_provenance.label` = prefix only; `reference_chips[].label` = full linkable citation (`api/reference_links.py`) |
| Frontend | `InlineCitationText` + `StandardReferenceLink variant="inline"` |

Wrong: `Resolved from Table A-1` [Standard reference]  
Correct: `Resolved from `**`ASME B31.3 Table A-1`** (only the citation is clickable)

### Do not

- Label derived quantities (e.g. pressure design thickness `t` required by §304.1.1 eq. 2) as awaiting user input when the graph already names the producing equation/paragraph.
- Hardcode paragraph ids in display code; resolve producers via `calculates_parameter` / `returns_parameter` edges and active-path filtering (`_node_active_on_path`).
- Duplicate producer-resolution logic in the frontend.
- Render references as detached chip rows below prose or as a separate generic link label beside duplicated citation text.

### Design references

- `docs/desktopApp/05_backend_ui_contract.md` — display output blocks
- [`audits/contracts/nodes/parameter.md`](../audits/contracts/nodes/parameter.md) — `parameter_class`, `resolution`
- `engine/graph/micro_graph_engine.py` — calculated parameters excluded from `required_user_inputs`

---

## 16. Lookup-derived parameters (table resolution)

**Parameters produced by lookup nodes must not be asked as direct user inputs or confirmed from invented defaults. Collect lookup key parameters first; resolve the output from the table at runtime.**

| Layer | Rule |
| --- | --- |
| Lookup node | `returns_parameter` edge to the global `PARAM-*` node; `lookup.keys` / `inputs[].id` name the prerequisite parameters |
| Parameter node | Describes the symbol only — no `default`, `metadata.default_value`, or confirmation prompts for table-derived values |
| `required_user_inputs()` | Excludes lookup outputs; includes only unresolved **lookup keys** (via `lookup_resolution_for_parameter`) |
| Coefficient / lookup execution | `apply_coefficient_lookups` / lookup engine writes table-sourced facts after keys are confirmed |
| Workflow `runtime.yaml` | Phase lists name lookup **dependencies** (e.g. `pipe_construction_type`), not derived coefficients (`weld_joint_efficiency`) |
| Messaging | Prompt copy asks for lookup keys only — never "confirm E = 1.0" or similar for table-derived outputs |

### Do not

- Propose or confirm table-derived coefficients (E, W, Y, S, …) before their lookup keys are satisfied.
- Author `default`, `metadata.default_value`, `source: default`, or `requires_confirmation` on lookup-output `PARAM-*` nodes or sidecar inputs.
- Add execution-assumption confirmation specs for lookup-derived parameter nodes in engine code.
- Author `introduces_parameter` to informal names (`quality_factor`) instead of `returns_parameter` → `PARAM-*`.

### Design references

- [`audits/contracts/nodes/lookup.md`](../audits/contracts/nodes/lookup.md) — lookup node contract
- `engine/graph/lookup_parameter_resolution.py` — infers `table_lookup` resolution from graph
- `engine/executor/coefficient_lookup.py` — ASME B31.3 coefficient table resolution
- §14 — parameter key consistency for lookup `inputs[].id`
- §15 — derived parameter value display (table link before value exists)

---

## 17. PARAM-driven composer metadata (no engine fallbacks)

**Every gatherable workflow parameter must have a global `PARAM-*` node. The desktop composer UI spec (label, type, units, static options, default value) comes from that node only — not from hardcoded engine maps or interaction fallbacks.**

| Layer | Rule |
| --- | --- |
| `PARAM-*` node | Required before the parameter appears in workflow phases, sidecars, or composer |
| `metadata.composer_input` | UI control: `number`, `dropdown`, `checkbox`, `material`, … |
| `metadata.composer_options` | Static `{value, label}` pairs for path decisions and categorical choices **only** (mutually exclusive with `table_options`) |
| `metadata.table_options` | Table-backed dropdown/search: `{table, query}` binding to a named `option_queries` profile on the table/catalog YAML |
| `parameter_class` + `dimension` | Default composer type when `composer_input` is omitted |
| `build_composer_parameter_spec()` | Sole resolver for label/type/units/static options; raises if PARAM node is missing |
| Table-backed option lists | Generic `engine/reference/table_options_resolver.py` executes parameterized SQL from table YAML `option_queries` — **not** per-parameter helpers in `api/parameter_definitions.py` |

### Static vs table-backed options (mutually exclusive)

| Pattern | PARAM metadata | Options source |
| --- | --- | --- |
| Static | `composer_options` only | Authored labels on the PARAM node (e.g. pressure loading) |
| Table-backed | `table_options` only | SQL via `option_queries` on table/catalog YAML |

Table-backed PARAMs must **not** declare `composer_options`. Unrestricted query profiles (no `requires` / `filter`) return **all** table rows by default; YAML `requires` / `filter` or task facts narrow the SQL.

See also §18-style table option rules: `.cursor/rules/table-options-queries.mdc`.

### Do not

- Add `_PARAMETER_SPECS`, `_LOOKUP_DEFAULT_UNITS`, or per-parameter `if parameter_id == …` type/unit/**options** maps in API or engine code.
- Add `_nps_dropdown_options`, `_pipe_schedule_dropdown_options`, or similar per-table API helpers.
- Declare both `composer_options` and `table_options` on the same PARAM node.
- Fall back to workflow `interactions` when PARAM metadata is absent.
- Author runtime field lists or `_PARAM_TO_FIELD` entries without a matching `PARAM-*.yaml` file.
- Put composer type or default-unit logic in the frontend.

### Design references

- `engine/reference/parameter_composer_spec.py` — PARAM-only composer resolver
- `api/parameter_definitions.py` — merges table-backed options from `table_options_resolver` onto PARAM-derived specs
- [`audits/contracts/nodes/parameter.md`](../audits/contracts/nodes/parameter.md) — composer metadata fields
- §14 — parameter `key` consistency
- `.cursor/rules/param-composer-metadata.mdc`

---

## 18. Lookup conditionals (table boundary rules)

**When a table lookup needs out-of-range behavior (clamp to endpoint, use boundary value, etc.), author `lookup_conditionals` on the output `PARAM-*` node — not in Python resolvers or lookup nodes.**

| Layer | Rule |
| --- | --- |
| Output `PARAM-*` node | `lookup_conditionals.<lookup_key>` with `unit`, `min`, `max`, `below_min`, `above_max` |
| Lookup node | Tabulated data and `interpolation` only; no temperature clamp metadata |
| Table DB / YAML | Store breakpoints only; no extrapolation policy |
| Engine | Generic interpreter in `engine/graph/lookup_conditionals.py` applies authored rules at lookup time |

Example (`PARAM-temperature-coefficient-Y`):

```yaml
lookup_conditionals:
  design_temperature:
    unit: UNIT-degF
    min: 900
    max: 1250
    below_min: use_min
    above_max: use_max
```

### Do not

- Hardcode table-specific temperature limits in `coefficient_resolver.py`, `lookup_engine.py`, or API code.
- Duplicate boundary rules on lookup nodes when they govern the derived parameter value.
- Add per-table clamp functions under `engine/reference/`.

### Design references

- `engine/graph/lookup_conditionals.py` — generic conditional interpreter
- `engine/graph/lookup_parameter_resolution.py` — exposes `lookup_conditionals` on resolution
- [`audits/contracts/nodes/parameter.md`](../audits/contracts/nodes/parameter.md) — `lookup_conditionals` on lookup outputs
- `.cursor/rules/lookup-conditionals.mdc`

---

## 19. Planner traversal debug state

**`PlannerTraversalState` on `EngineeringPlan` is for inspector debugging of planner graph walk — not execution trace, not final requirement lists alone.**

| Layer | Rule |
| --- | --- |
| `engine/planner/planner_traversal.py` | Derive traversal from requirements, `input_strategy`, graph preview, path decisions |
| `EngineeringPlan.traversal` | Persist full state on `task.outputs.engineering_plan` |
| `planner_inspector_summary` | Rebuilt from `engineering_plan` on each inspection payload — **not** from `goal_store` (backward compat) |
| `planner_debug_projection` | Read-only Dev Mode Planner tab contract — derived from `engineering_plan` only; never drives execution |
| `current_active_node_id` | Must match next **askable** planner input (`user_input` / `branch_decision`); never an equation output PARAM while inputs are missing |
| `pending_expansion_nodes` | **Single pending queue** on `PlannerTraversalState`. Each item has `status_reason` and optional `waiting_on`. Holds gatherable PARAM nodes, equations awaiting inputs, and branch-waiting nodes — not ruled-out exclusions |
| `expanded_nodes` | Nodes already visited/expanded in this planner walk |
| `traversal_events` | Include `parameter_resolved` for resolved gatherable fields |
| `plan_validation.py` | Generic invariants after `finalize_engineering_plan()`; errors on `plan.debug` |

### Pending queue contract (no duplicate membership)

A node id may appear in **at most one** live traversal bucket among: `current_active_node_id`, `pending_expansion_nodes`, `expanded_nodes`, or excluded (ruled-out expansion).

| Bucket | Meaning |
| --- | --- |
| `pending_expansion_nodes` | Queued / blocked / awaiting-input nodes with `status_reason` (+ `waiting_on` when blocked on another node or gate) |
| `expanded_nodes` | Already handled in this walk |
| Excluded | Ruled out by expansion or branch — **must not** also appear in `pending_expansion_nodes` |

`planner_debug_projection.groups.queue_leaf_nodes` is a **derived inspector view** from `pending_expansion_nodes` and traversal events — not a second authoritative queue. `blocked_nodes` is deprecated (empty); blocked nodes appear only in the pending queue with an explicit `status_reason`.

Named projection groups: `visited_previous_step`, `queue_leaf_nodes`, `visited_from_beginning`, `excluded_nodes` (plus deprecated empty `blocked_nodes` for backward compat).

### API / inspector contract

| Field | Role |
| --- | --- |
| `engineering_plan` | Canonical normalized plan (`plan.to_dict()`) — **source of truth** |
| `engineering_plan_view` | Human-readable inspector summary (phases, overview) |
| `planner_inspector_summary` | Compact planner debug (backward compat): root goal, phase, inputs, traversal summary |
| `planner_debug_projection` | Preferred Dev Mode Planner tab UI contract; `raw_planner_state` for Advanced JSON only |
| `legacy_goal_map` | Optional backward-compatible `goal_store` projection (`GOAL-*` / `REQ-*` keys) — debug panel only |

Do not expose the legacy goal map as `engineering_plan` or as the default planner output.

### Planner inspector summary (`build_planner_inspector_summary`)

Derived from `EngineeringPlan` only (`engine/planner/plan_inspector.py`):

- `root_goal`, `current_phase`, `next_input` (one field in `single_next_question` mode)
- `outstanding_required_inputs` (future active fields; not a full `next_required_inputs` list)
- `conditional_requirements`, `derived_or_lookup_values`, `calculations`
- `planner_graph_summary`, `traversal_summary`, `planner_traversal_view`
- `warnings` (includes validation errors when present)

Inspection API rebuilds summary via `planner_inspector_summary_for_task()` and projection via `planner_debug_projection_for_task()` (`engine/inspection/builder.py`).

Dev UI: **Planner / Workflow Debug** tab (`PlannerDevPanel`) reads **`planner_debug_projection` only** — no client inference from `engineering_plan`, `task_state`, or other payload fields. Missing fields render **"not available"**. Raw state is collapsed under **Advanced Planner JSON** (`raw_planner_state`). `planner_inspector_summary` remains on the payload for backward compatibility.

`planner_debug_projection` is **read-only and developer-only** — it must never drive workflow execution, user-facing output, graph traversal, equation evaluation, validation, or parameter resolution.

### Do not

- Use traversal state to drive workflow paths or parameter asks (graph expansion + `input_strategy` remain authoritative).
- Point `current_active_node_id` at coefficient lookup `PARAM-*` nodes while expansion/path gates are unresolved.
- Duplicate graph engine execution order in traversal events without planner context.
- Default the planner inspector to `planning_summary` or flat `GOAL-*` / `REQ-*` maps.

### Design references

- `engine/planner/planner_traversal.py` — builder and inspector view helpers
- `engine/planner/plan_inspector.py` — `build_planner_inspector_summary`, `planner_inspector_summary_for_task`
- `engine/planner/planner_debug_projection.py` — `build_planner_debug_projection`, `planner_debug_projection_for_task`
- `dev/desktop_ui/inspector/PlannerDevPanel.tsx` — renders projection sections only
- `models/engineering_plan.py` — `PlannerTraversalState` types
- `docs/developer_inspection_framework.md` — Planner tab
- `tests/planner/test_planner_traversal.py`, `tests/planner/test_planner_debug_projection.py`
- Workflow-specific acceptance: [`docs/workflows/pipe_wall_thickness/acceptance_contract.md`](workflows/pipe_wall_thickness/acceptance_contract.md)

---

## 20. Engineering plan validation

**Normalized planner output must pass `validate_engineering_plan()` before consumers treat it as canonical.**

| Check | Rule |
| --- | --- |
| Structure | `root_goal`, `requirements`, `dependencies`, `input_strategy`, `phases`, `graph`, `traversal` required |
| Not a flat map | Top-level `GOAL-*` / `REQ-*` keys without nested `requirements` are invalid |
| `blocked_by` / `provisional_blocked_by` | Every id must exist in `requirements` |
| Dependencies | Endpoints: requirement id, root goal id, or alternative id (`activates` source only) |
| Requirements | No legacy fields (`satisfaction`, `state`, `metadata`, `edges`, …) |
| `single_next_question` | `next_fields.length <= 1`; at most one active phase; next field in `current_phase` |
| Traversal | Active node required; pending ∩ expanded = ∅; branch paragraphs not expanded before branch resolves |
| Alternatives | Each alternative id must exist; diameter and lookup-input dependency rules enforced in `plan_validation.py` |

Validation runs after `finalize_engineering_plan()` (dependencies populated). Failures are stored on `plan.debug.validation_errors` / `validation_warnings` and surfaced in the Planner dev tab.

Workflow-specific requirement ids, phase expectations, and test inventories for `pipe_wall_thickness_design` live in [`docs/workflows/pipe_wall_thickness/acceptance_contract.md`](workflows/pipe_wall_thickness/acceptance_contract.md) — not in this section.

| API | Role |
| --- | --- |
| `validate_engineering_plan(plan)` | Python — `PlannerValidationResult` |
| `validate_engineering_plan_dict(raw)` | Python — rejects flat legacy maps |
| `validateEngineeringPlan(plan)` | TypeScript — `dev/desktop_ui/inspector/validateEngineeringPlan.ts` |

### Tests

- `tests/planner/test_plan_validation.py` — generic dependency and structure invariants
- `tests/planner/test_planner_output_shape.py` — canonical vs `legacy_goal_map`
- `dev/desktop_ui/tests/validateEngineeringPlan.test.tsx` — client validator
- Workflow acceptance tests: [`docs/workflows/pipe_wall_thickness/acceptance_contract.md`](workflows/pipe_wall_thickness/acceptance_contract.md)

### Design references

- `engine/planner/plan_validation.py`
- `docs/rules.md` §19–§20 — planner inspector and validation rules

---

## 21. Flow Guidance Layer (traversal narration)

**User-facing traversal narration lives in the Flow Guidance Layer — not in the planner, graph engine, engineering nodes, desktop/API presentation code, or deterministic parameter prompt builders.**

The Flow Guidance Layer explains *why* the system is moving through a workflow, *why* a node is being evaluated, and *what* the user should expect next. It is presentation-only data and code.

### Components

| Component            | Module                                     | Owns                                                                                                                                               | Does not own                                                      |
| -------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **GuidanceResolver** | `engine/presentation/guidance_resolver.py` | Traversal narration from `presentation/guidance/workflows/*.yaml` keyed by workflow context                                                        | Parameter prompts, equation bodies, planner copy, graph traversal |
| **ResponseComposer** | `engine/presentation/response_composer.py` | Merging guidance blocks + deterministic messaging prompts + validation warnings + node/equation asset references into UI-neutral structured output | Planning, graph traversal, validation, execution                  |
| **Types**            | `models/presentation.py`                   | `GuidanceBlock`, `GuidanceContext`, `PresentationBlock`, `PresentationResponse`                                                                    | Engineering truth                                                 |

### GuidanceResolver inputs (allowed)

Resolve narration from:

- `workflow_id`
- `current_phase`
- `active_node_id`
- `node_role`
- `traversal_event`
- `edge_reason`
- task state metadata required for template matching only, such as confirmed inputs, current phase, selected branch, warnings, and active task id

`PlannerTraversalState` may supply `traversal_event` and `active_node_id` as **context facts only**. Its `message` fields are debug copy — **must not** become user-facing guidance.

### GuidanceResolver outputs

Structured `GuidanceBlock` objects (`source: "guidance"`). Blocks may **reference** `node_id`, `equation_id`, `table_id`, or `paragraph_id` in `refs` — they must not embed engineering truth.

### ResponseComposer outputs

`PresentationResponse` with:

| Field                 | Meaning                                                                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `presentation_blocks` | Rebuilt current presentation snapshot for the current task/workflow state. **Owned by `PresentationResponse`, not by workflow logic.** |
| `transcript_blocks`   | **Append-only** historical conversation/output blocks                                                                                   |
| `active_prompt`       | The current deterministic ask block produced by `engine/messaging/`. It is not guidance YAML and is not historical transcript content until displayed/appended. |

Output must be **UI-neutral** structured blocks (dict/JSON-serializable). Desktop, API, and chat orchestration consume the same `PresentationResponse` shape via `task_state.flow_guidance` and chat-turn payloads.

### Distinction: `presentation_blocks` vs `transcript_blocks`

|           | `presentation_blocks`                                                                 | `transcript_blocks`                                            |
| --------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Lifecycle | Rebuilt each turn from current state                                                  | Append-only; never overwrite prior entries                     |
| Ownership | `PresentationResponse` — not workflow state, not a presentation store on the task   | Session/conversation history                                   |
| Content   | Current phase snapshot (parameters, equations, warnings)                              | Historical guidance, equations, explanations shown to the user |
| Tests     | Use field name `presentation_blocks`                                                  | Use field name `transcript_blocks` — never conflate            |

Changing `presentation_blocks` after a phase advance must **not** erase `transcript_blocks`. Do **not** attach presentation state directly to workflow state.

Block identity, in-place updates, equation atomic units, and scroll ordering: **§25**.

### Guidance YAML (`presentation/guidance/workflows/`)

**Allowed:** traversal narration, branch context, “what happens next” prose, references to node/equation/table/paragraph ids.

**Forbidden:**

- Deterministic parameter/formula prompt copy (owned by `engine/messaging/formula_parameter_prompt.py` and related prompt builders: `step_prompt.py` and desktop/API `parameter_input_prompt.py`)
- Duplicates of `build_step_prompt()`, `build_formula_parameter_prompt()`, or `build_parameter_input_prompt()` output
- Equation bodies, LaTeX, or formula text (reference `equation_id` only)
- Verbatim paragraph engineering text from knowledge nodes
- Planner `PlannerTraversalState.message` strings
- Hardcoded chat-orchestrator or API presentation strings outside `presentation/guidance/` and `engine/messaging/`

Guidance templates are **presentation data**, not engineering truth.

### Deterministic prompts (unchanged — §12)

Parameter and step prompt text remains owned by `engine/messaging/`:

- `build_parameter_input_prompt()`
- `build_step_prompt()`
- `build_formula_parameter_prompt()`

ResponseComposer **combines** guidance with these prompts; it does not replace them.

### Layer restrictions

| Layer                            | Must not store workflow-specific guidance copy                          |
| -------------------------------- | ----------------------------------------------------------------------- |
| Planner (`engine/planner/`)      | Yes                                                                     |
| Graph Engine (`engine/graph/`)   | Yes                                                                     |
| Engineering nodes (`knowledge/`) | Yes (intrinsic assets only: paragraph text, equation intro, `ai_hints`) |
| API / Desktop / chat orchestration | Display structured blocks, collect input                              |
| Workflow state / task model      | Yes — do not make workflow state a presentation store                   |

State/session storage may persist `transcript_blocks`, but it must **not** derive engineering meaning from them. Transcript blocks are display history only.

### Do not

- Let `presentation_blocks` become part of workflow logic.
- Let guidance YAML become another prompt system.
- Let planner/debug messages become user-facing guidance.

### Tests

- `tests/presentation/test_guidance_resolver.py`
- `tests/presentation/test_response_composer.py`
- `tests/api/test_append_only_transcript_blocks.py`
- `tests/api/test_guidance_blocks.py`
- `tests/api/test_chat_orchestrator.py`

### Design references

- `docs/core/5. workflow_design.md` — phased input + Flow Guidance Layer
- `api/flow_guidance.py` — `task_state["flow_guidance"]` payload
- `api/chat_orchestrator.py` — chat-turn composition + `new_transcript_blocks`
- `docs/core/11. planner_layer_design.md` — planner vs guidance boundary
- `docs/core/14. graph_engine_design.md` — graph vs guidance boundary
- `engine/presentation/README.md` — module inventory

---

## 22. Plan Review Gate

Every Cursor feature plan must include a visible **Plan Review Gate** section inside the plan itself — **after** the Architecture Consistency Review (§23), before any implementation begins.

**Purpose:** Give non-technical reviewers (project owner, CEO, product manager) a plain-English check on safety, architecture alignment, testability, and implementation readiness — without copying the plan to an external tool.

**Cursor rules:** `.cursor/rules/plan-review-gate.mdc`, `.cursor/rules/feature-planning.mdc`  
**Process doc:** `docs/process/plan_review_gate.md`

### Who assigns status

| Actor | May assign | May not assign |
| --- | --- | --- |
| **Cursor** | **READY_FOR_REVIEW**, **REVISE**, **BLOCKED** | **APPROVED** |
| **Project owner** | **APPROVED**, **REVISE**, **BLOCKED** | — |

Cursor self-certification is not allowed. A plan Cursor marks **READY_FOR_REVIEW** is a draft for human review — not permission to implement.

### Status meanings

| Status | Cursor may set | Implementation |
| --- | --- | --- |
| **READY_FOR_REVIEW** | Yes | Not allowed — awaits project-owner review |
| **REVISE** | Yes | Not allowed — correct the plan first |
| **BLOCKED** | Yes | Not allowed — resolve missing decisions first |
| **APPROVED** | **No** | Allowed **only** after project owner grants approval **and** the user gives an explicit implementation instruction |

### Required plan sections (before the gate)

- Feature summary and user-visible behavior
- Allowed files/modules vs out-of-scope layers
- Acceptance criteria in plain English
- Test plan (general, workflow-specific, regression, user-visible output)
- **Architecture Consistency Review** (§23) — status must be **CLEAR** before seeking **APPROVED**

### Required gate sections

Status, Plain-English Summary, Business/User Impact, Architecture Alignment, Main Risks, Missing Decisions, Test Coverage Required, Documentation / Rules Updates Required, Out of Scope, Implementation Permission.

### Implementation Permission (Cursor)

Cursor must end with exactly one of:

- "Implementation not allowed — plan is **READY_FOR_REVIEW**; awaiting project-owner approval."
- "Implementation not allowed until the plan is revised."
- "Implementation blocked until the missing decision is resolved."

Only the project owner may write "Implementation allowed." after setting status **APPROVED**.

### Status assignment (summary)

- Architecture Consistency Review not **CLEAR** → Cursor sets **REVISE** or **BLOCKED** (see §23 Phase 0 sequence)
- Missing tests → **REVISE**
- Unclear architecture boundaries → **REVISE**
- Unrelated layer changes → **REVISE** or **BLOCKED**
- UI/output fix via Planner, Graph, Execution, or engineering nodes (unjustified) → **REVISE**
- General feature tested only on one workflow → **REVISE**
- Hardcoding `pipe_wall_thickness_design` in general components → **REVISE**
- Guidance/prompts in wrong layer → **REVISE** (see §12, §21)
- Broad scope without split steps → **REVISE** or **BLOCKED**
- Plan looks sound to Cursor → **READY_FOR_REVIEW** (never **APPROVED**)

Full template, decision rules, compliance checklist, and example: `.cursor/rules/plan-review-gate.mdc`.

---

## 23. Architecture Consistency Review

Every Cursor feature plan must include a visible **Architecture Consistency Review** section **before** the Plan Review Gate — inside the plan itself, not in a separate file.

**Purpose:** Surface architectural conflicts with `docs/rules.md` and aligned design docs in plain English for non-technical reviewers, before implementation begins.

**Cursor rules:** `.cursor/rules/plan-review-gate.mdc`, `.cursor/rules/feature-planning.mdc`  
**Process doc:** `docs/process/plan_review_gate.md`

### Required section format

```markdown
# Architecture Consistency Review

| Field | Value |
| --- | --- |
| Existing source files checked | … |
| Possible conflicts found | … |
| Conflicting source of truth | … |
| Proposed resolution | … |
| User impact | … |
| Risk if ignored | … |
| Required doc/rule/test updates | … |
| Status | CLEAR / NEEDS_DOC_UPDATE / NEEDS_DECISION / BLOCKED |
```

### Status behavior

| Status | Meaning | Next step |
| --- | --- | --- |
| **CLEAR** | No architectural conflicts detected | Cursor may set Plan Review Gate to **READY_FOR_REVIEW** |
| **NEEDS_DOC_UPDATE** | Docs are inconsistent but intended architecture is clear | **Phase 0 only** — documentation fixes; no feature implementation |
| **NEEDS_DECISION** | Two sources of truth conflict with no clear winner | Cursor sets gate **REVISE** or **BLOCKED** |
| **BLOCKED** | Implementation would violate `docs/rules.md` | Cursor sets gate **BLOCKED** |

If status is not **CLEAR**, Cursor must not set the Plan Review Gate to **READY_FOR_REVIEW** or **APPROVED**. Only the project owner may grant **APPROVED**, and only after **CLEAR**.

### NEEDS_DOC_UPDATE sequence (mandatory)

When the consistency review is **NEEDS_DOC_UPDATE**:

1. **Phase 0 — documentation only.** Limit the plan to editing the conflicting docs, rules, or audit notes listed under Required doc/rule/test updates. No production feature code.
2. **Apply the documentation fixes** in the allowed files only.
3. **Repeat the Architecture Consistency Review** on the updated sources.
4. **Require CLEAR** before any feature implementation plan proceeds.
5. **Seek implementation approval** — Cursor sets **READY_FOR_REVIEW**; project owner grants **APPROVED**; user gives an explicit implementation instruction.

Doc fixes and feature work must not ship in the same implementation step.

### Compliance checklist (must answer in every plan)

1. Does this plan introduce hardcoded workflow fields, branch IDs, paragraph IDs, or frontend engineering logic?
2. Does this plan ask for lookup-derived outputs instead of lookup keys?
3. Does this plan bypass `PARAM-*` metadata for gatherable parameters?
4. Does this plan put prompt copy in the planner, graph engine, execution layer, API serializers, or frontend?
5. Does this plan put traversal narration outside the Flow Guidance Layer?
6. Does this plan add fixed required input lists where graph expansion should decide active inputs?
7. Does this plan use old node layout instructions as if they are current?
8. Does this plan confuse `RuleEngine` with `ValidationEngine`?
9. Does this plan use legacy planner/goal maps as canonical output?
10. Does this plan require doc/rule/test updates before implementation?

If any answer indicates a violation, Cursor must set the Plan Review Gate to **REVISE** or **BLOCKED** — not **READY_FOR_REVIEW** or **APPROVED**.

Full template and integration rules: `.cursor/rules/plan-review-gate.mdc`, `docs/process/plan_review_gate.md`.

---

## 24. Equation display trace (evaluated equation substitution)

**Every evaluated equation must expose a canonical `equation_display_trace` object built in the execution layer and rendered by API/presentation/frontend without client-side substitution.**

| Layer | Owns |
| --- | --- |
| Execution (`engine/equation/`, `engine/executor/node_runner.py`) | Build `equation_display_trace` from equation metadata, resolved facts, `CalculationResult`, optional `render_steps` enrichment |
| API (`api/equation_display_trace_serializer.py`, `api/equation_evaluation_display.py`) | Serialize trace onto `EquationOutputBlock`; emit legacy substitution output **only** when `equation_display_trace` is absent |
| Presentation (`engine/presentation/blocks.py`, `engine/graph/display_emitter.py`) | Same trace object on equation result blocks |
| Frontend (`EquationOutput`) | Render `equation_display_trace` only; no engineering formatting or symbol substitution in TypeScript |

### Canonical field

- `equation_display_trace` on execution trace payloads and equation output blocks.
- `EquationOutputBlock` mirrors the trace schema; do not invent competing display fields.

### LaTeX source priority

1. `display_latex` metadata
2. Authored `display.text` (equation content only)
3. SymPy reconstruction (mark `latex_source: sympy_generated`)

Shared formatting: `engine/equation/latex_format.py` (`\mathrm{}` units, numeric display strings).

### Legacy substitution fallback (strict)

- Legacy substitution output may be emitted **only** when `equation_display_trace` is absent on that equation block for the current task state.
- The canonical trace and legacy substitution block **must never both** be emitted for the same equation and task state.
- **Remove the fallback** when every equation on active workflow paths builds `equation_display_trace` in execution and API regression tests pass without legacy substitution fields (`tests/api/test_equation_display_trace.py`, `tests/api/test_display_block_lifecycle.py`, `tests/equation/test_equation_display_trace_builder.py`).

### Do not

- Build per-equation KaTeX substitution strings in `api/equation_inputs_display.py` for new equations.
- Emit legacy substitution alongside `equation_display_trace` on the same block.
- Reconstruct substitutions in the frontend.
- Store presentation-only equation state on `WorkflowState`.

### Input provenance on trace rows

`equation_display_trace.inputs[].source_type` is defined in `models/equation_display_trace.py` (`user_input`, `table_lookup`, `equation_output`, `default`, `system`). §15–§16 govern when to show reference links vs awaiting-input in equation **input tables** — not this trace schema.

### Design references

- `models/equation_display_trace.py` — canonical dataclasses and `source_type` enum
- `engine/equation/equation_display_trace_builder.py` — generic builder

---

## 25. Rendered block lifecycle (identity, persistence, ordering)

**Every user-visible output block follows deterministic identity and merge rules.** This section is the architecture rule; field-level detail lives in [`docs/desktopApp/center_panel_output_contract.md`](desktopApp/center_panel_output_contract.md).

### Identity

- Every **durable** block has a deterministic `block_id` (stable `id` on the block payload).
- The same `block_id` identifies one logical block for the life of the task (until completion policy freezes the transcript).
- Guidance entry ids, equation node ids, and trace keys must produce stable ids — see center-panel contract for patterns (`equation-{equation_node_id}`, `guidance-{workflow_id}-{entry_id}`, …).

### Update vs append

- When content for an existing durable `block_id` changes, **update the block in place** — do not append a second copy with the same id.
- `transcript_blocks` append **new** `block_id`s only. Re-fetching task state (`get_task`, reload, projection refresh) must **not** duplicate durable blocks already in transcript or `display_outputs`.
- `presentation_blocks` / `display_outputs` may rebuild each turn; durable history in `transcript_blocks` remains append-only (§21).

### Equation atomic unit

An equation render unit is **one block** with stable `equation-{equation_node_id}` (or equivalent stable id). It contains, in order:

1. Symbolic equation
2. Parameter input table
3. Substituted expression (when inputs resolve)
4. Evaluated result line

These are progressive content on the **same** block via `equation_display_trace` — not separate scroll blocks.

### Equation chain (visited nodes, upstream dependents)

- **Every visited equation node** creates or updates **one** equation block at stable `equation-{equation_node_id}`. First visit may be preview-tier; evaluation upgrades that same block to durable in place — never a second visible block for the same equation.
- A **later dependent equation** must **not** replace or remove an **upstream** equation block. Each equation in the dependency chain keeps its own stable `block_id`; advancing to a dependent equation only creates or updates **that** equation's block.
- **Previously evaluated equations must remain visible** when later equations are visited or evaluated (see also preview vs evaluated below).

### Preview vs evaluated (no double emit)

- **Preview** and **evaluated** forms of the same equation must **not** appear as two separate visible blocks at once.
- When evaluation completes, the stable equation block upgrades (`display_state`: `preview` → `evaluated`, lifecycle: `preview` → `durable`) in place.

### Prompts vs equation blocks

- Input prompts (`current_ask`, `active_prompt`, `ask_archive`) belong in the **composer** or transcript archive roles — **not** sorted inside an equation render unit.
- Parameter-table row order follows equation/graph input order; do not interleave unrelated prompt blocks into the equation block.

### Rendering order

- Scroll and report order follow **authored traversal / display history order** (`DISPLAY_ROLE_ORDER`, `contracts/center_panel_report_role_order.json`, chronological append within role).
- Do **not** reorder visible blocks by reconstruction order (build pass order, dict iteration, or frontend merge discovery order).

### Layer ownership

| Concern | Owner |
| --- | --- |
| Stable `block_id` assignment, dedupe, in-place merge | API (`api/output_blocks.py`, `api/display_block_metadata.py`, `api/center_panel_contract.py`) |
| Durable transcript persistence | `api/flow_guidance_sync.py`, `task.outputs["flow_guidance_transcript"]` |
| Scroll assembly | `assemble_center_panel_scroll_blocks` / `buildCenterPanelTranscript.ts` |
| Render trace only | Frontend (`EquationOutput`) — no substitution logic |

### Tests

- `tests/api/test_display_block_lifecycle.py`
- `tests/api/test_pipe_wall_output_lifecycle.py`
- `tests/api/test_center_panel_display_sequence.py`
- `tests/api/test_append_only_transcript_blocks.py`
- `desktopApp/tests/utils/centerPanelContractSync.test.ts`
