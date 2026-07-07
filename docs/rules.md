# Engineering Desktop — Agent and Implementation Rules

Source of truth for Cursor agents and contributors. `.cursor/rules/agent-rules.mdc` mirrors the section list here; do not contradict this file.

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

Prove fixes with tests that exercise real behavior. After API/backend changes: `python -m pytest tests/api tests/mvp/test_desktop_mvp_workflow.py`. After desktop UI changes: `cd desktopApp && npm run test:run` and MVP smoke when relevant.

---

## 6. Goal-driven execution

Define success criteria and a short plan for non-trivial work before coding.

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
- Use node templates under `docs/node-templates/`.
- Confirm template or relationship-schema changes with the user.
- Paragraph subsection naming: `.cursor/rules/paragraph-subsection-naming.mdc`.

---

## 12. User-facing prompts (planner vs messaging)

**The planner decides what to ask next; it does not own prompt copy.**

| Layer | Owns | Does not own |
| --- | --- | --- |
| **Planner** (`engine/planner/`) | Navigation phases, missing-field order, submittable parameter ids, goal tree structure | User-facing question strings, autocomplete labels, material search hints |
| **Messaging** (`engine/messaging/`) | Deterministic prompt text, resolution order, default catalog copy | Which parameter is active, phase gating, graph execution |

### Where prompt text lives

- **Workflow interaction specs** — `interactions` on workflow sidecars / `runtime.yaml` (highest priority when present).
- **Graph / parameter nodes** — `question` or `description` on parameter nodes.
- **Equation context** — `engine/messaging/formula_parameter_prompt.py`.
- **Default catalog** — `engine/messaging/workflow_parameter_prompts.py` (`DEFAULT_WORKFLOW_PARAMETER_PROMPTS`).
- **LLM agent stubs** — `ai/prompts/` (intent/planner agents only; not desktop parameter asks).

### Resolution entry point

All desktop/API parameter asks must resolve through:

`engine/messaging/parameter_input_prompt.build_parameter_input_prompt()`

Order inside that function (do not bypass or reorder without updating docs and tests):

1. Workflow interaction spec (`question_for_interaction`)
2. Graph parameter node question
3. Equation guidance
4. Legacy `phase_questions` on planning (backward compatibility only)
5. `default_workflow_parameter_prompt()` from `workflow_parameter_prompts.py`

### Do not

- Add or edit user-facing parameter prompt strings in `engine/planner/planner.py`, `goal_migration.py`, or serializers as the **source of truth**.
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
- Derive **which parameters to ask** from active parameter nodes and nomenclature on the expanded path (`required_user_inputs()`), plus execution-assumption evaluation — not from a fixed per-workflow field list.
- **Replan after each confirmed input** so branch-specific parameters (e.g. external design pressure) disappear when that branch is ruled out.
- Use navigation config **only** for phase ordering and gate-phase fields, never to inject path-specific parameters that the graph did not expand.

### Do not

- Hardcode paragraph ids, branch ids, or task field names in planner, serializers, `workflow_timeline.py`, `workflow_bootstrap.py`, or graph explorer projectors to select execution paths.
- List all branch parameters unconditionally in `runtime.yaml` `navigation.phases.parameter_gathering`.
- Merge static navigation phase lists over graph-derived `required_user_inputs` (gate phases only).
- Encode workflow branching in TypeScript or `if workflow == "pipe_wall_…"` blocks in the backend.
- Add new path logic only in the graph explorer frontend; backend expansion must enforce the same rules.

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
| Workflow `runtime.yaml` | Same key in phase field lists |
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
- Frontend: `EquationOutput` renders `value_reference` with `StandardReferenceLink` in the Value column (same link component as definition references).

### Do not

- Label derived quantities (e.g. pressure design thickness `t` required by §304.1.1 eq. 2) as awaiting user input when the graph already names the producing equation/paragraph.
- Hardcode paragraph ids in display code; resolve producers via `calculates_parameter` / `returns_parameter` edges and active-path filtering (`_node_active_on_path`).
- Duplicate producer-resolution logic in the frontend.

### Design references

- `docs/desktopApp/05_backend_ui_contract.md` — display output blocks
- `docs/node-templates/Parameter Node.md` — `parameter_class`, `resolution`
- `engine/graph/micro_graph_engine.py` — calculated parameters excluded from `required_user_inputs`

---

## 16. Lookup-derived parameters (table resolution)

**Parameters produced by lookup nodes must not be asked as direct user inputs or confirmed from invented defaults. Collect lookup key parameters first; resolve the output from the table at runtime.**

| Layer | Rule |
| --- | --- |
| Lookup node | `returns_parameter` edge to the global `PARAM-*` node; `lookup.keys` / `inputs[].id` name the prerequisite parameters |
| Parameter node | Describes the symbol only — no `default: 1.0` or confirmation prompts for table-derived values |
| `required_user_inputs()` | Excludes lookup outputs; includes only unresolved **lookup keys** (via `lookup_resolution_for_parameter`) |
| Coefficient / lookup execution | `apply_coefficient_lookups` / lookup engine writes table-sourced facts after keys are confirmed |
| Workflow `runtime.yaml` | Phase lists name lookup **dependencies** (e.g. `pipe_construction_type`), not derived coefficients (`weld_joint_efficiency`) |
| Messaging | Prompt copy asks for lookup keys; never "confirm E = 1.0" unless the node explicitly authors that default |

### Do not

- Propose or confirm table-derived coefficients (E, W, Y, S, …) before their lookup keys are satisfied.
- Use `source: default` / `requires_confirmation` on sidecar inputs for lookup outputs.
- Add execution-assumption confirmation specs for lookup-derived parameter nodes in engine code.
- Author `introduces_parameter` to informal names (`quality_factor`) instead of `returns_parameter` → `PARAM-*`.

### Design references

- `docs/node-templates/lookup.md` — lookup node template
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
| `metadata.composer_options` | Static `{value, label}` pairs for path decisions and categorical choices |
| `metadata.canonical_unit` | Default unit (`UNIT-mm`, `NPS`, …) |
| `metadata.default_value` | Proposed default (e.g. straight-pipe assumption `true`) |
| `parameter_class` + `dimension` | Default composer type when `composer_input` is omitted |
| `build_composer_parameter_spec()` | Sole resolver; raises if PARAM node is missing |
| Dynamic option lists | NPS / schedule / catalog options loaded from databases in `parameter_definitions.py` **after** PARAM establishes type — not a missing-node fallback |

### Do not

- Add `_PARAMETER_SPECS`, `_LOOKUP_DEFAULT_UNITS`, or per-parameter `if parameter_id == …` type/unit maps in API or engine code.
- Fall back to workflow `interactions` when PARAM metadata is absent.
- Author runtime field lists or `_PARAM_TO_FIELD` entries without a matching `PARAM-*.yaml` file.
- Put composer type or default-unit logic in the frontend.

### Design references

- `engine/reference/parameter_composer_spec.py` — PARAM-only composer resolver
- `api/parameter_definitions.py` — merges dynamic lookup options onto PARAM-derived specs
- `docs/node-templates/Parameter Node.md` — composer metadata fields
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
- `docs/node-templates/Parameter Node.md` — `lookup_conditionals` on lookup outputs
- `.cursor/rules/lookup-conditionals.mdc`

---

## 19. Planner traversal debug state

**`PlannerTraversalState` on `EngineeringPlan` is for inspector debugging of planner graph walk — not execution trace, not final requirement lists alone.**

| Layer | Rule |
| --- | --- |
| `engine/planner/planner_traversal.py` | Derive traversal from requirements, `input_strategy`, graph preview, path decisions |
| `EngineeringPlan.traversal` | Persist full state on `task.outputs.engineering_plan` |
| `planner_inspector_summary` | Compact `traversal_summary` + `planner_traversal_view` for dev UI |
| `current_active_node_id` | Must match next planner ask; follows phase order (assumptions → path → gathering → coefficients → equations) |
| `pending_expansion_nodes` | Include nodes blocked by unresolved gates/branches with `waiting_on` + `reason` |
| `plan_validation.py` | Invariants: active node in state, no duplicate/overlapping pending vs expanded, branch nodes not active early |

### Do not

- Use traversal state to drive workflow paths or parameter asks (graph expansion + `input_strategy` remain authoritative).
- Point `current_active_node_id` at coefficient lookup `PARAM-*` nodes while expansion/path gates are unresolved.
- Duplicate graph engine execution order in traversal events without planner context.

### Design references

- `engine/planner/planner_traversal.py` — builder and inspector view helpers
- `models/engineering_plan.py` — `PlannerTraversalState` types
- `docs/developer tools/developer_inspection_framework.md` — Planner traversal panel
- `tests/planner/test_planner_traversal.py`

