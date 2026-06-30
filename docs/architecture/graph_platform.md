# Graph Platform Architecture

Ver03 treats engineering standards as a **static micro-graph** compiled from Markdown/YAML sources. Runtime task state holds user values; the graph defines structure, dataflow, and conversion rules.

## Pipeline

```
standards/*/nodes/**/node.{yaml,md}  →  GraphBuilder  →  PackGraph  →  optional SQLite cache
                                                              ↓
                                                         GraphStore
                                                              ↓
                                                    MicroGraphEngine / Executor
                                                              ↓
                                                         Task (inputs/outputs)
                                                              ↓
                                                    WorkflowState (serializable view)
                                                              ↓
                                              display_emitter / API / Report generator
```

Sources are authoritative. Section nodes use a **single `node.yaml`** (YAML frontmatter + optional markdown body). Legacy table/note nodes may use `node.md` only. Embedded children in metadata containers compile as first-class nodes via `engine/reference/embedded_nodes.py`.

SQLite (`*_graph.db`) is a performance cache only; rebuild with `python scripts/build_graph_db.py`.

`WorkflowState` (`models/workflow_state.py`) is built from `Task` via `TaskStateManager.get_workflow_state()` — a read-only runtime boundary for serialization and future presentation/report cutover. Execution still mutates `Task` directly today.

## Static vs runtime

| Layer | Owns |
|-------|------|
| **PackGraph** | Node definitions, semantic edges, unit ontology, aliases |
| **Task** | User-entered values, calculation results, workflow progress (mutable store) |
| **WorkflowState** | Serializable snapshot: variable values, lookups, selections, history |
| **ExecutionPlan** | Ordered nodes for one evaluation pass (rebuilt per input set) |

The graph is never mutated during execution.

## Phase 1 implementation status

| Design principle | Enforcement |
|------------------|-------------|
| Graph is source of truth | YAML/MD → `GraphBuilder` → `PackGraph`; SQLite is cache-only |
| Nodes immutable | `normalize_node_metadata()` strips runtime fields on `quantity`/`designation` |
| Runtime in Workflow State | `WorkflowState` adapter over `Task`; exposed via API `workflow_state` field |
| Knowledge vs execution | `NodeRunner` skips reference-only types; equations execute via sympy |
| Render ≠ execute | `display_emitter` produces blocks; no formal event bus yet |
| LLM only via Ask AI | UI policy; not enforced in traversal |

## Canonical node types

| Type | Role |
|------|------|
| `workflow` | Root orchestration; anchors sections and goal outputs |
| `definition` | Standard paragraph anchor; nomenclature, expansion gates, child references |
| `calculation` | Executable section; parameter refs, equations, conditions |
| `quantity` | Physical engineering quantity (pressure, diameter, stress) — no runtime values |
| `designation` | Engineering designation (NPS, schedule, flange rating) — not a quantity |
| `parameter` | Task-state binding; `input_id` maps to Workflow State; `references` → quantity/designation |
| `equation` | Calculations and table lookups (`kind: calculation` or `lookup`) |
| `text` | Sections, tables, explanatory content (`kind: section`, `table`, `content`, `note`) |
| `unit` | Global unit ontology (pack: `standards/units/`) |

Legacy on-disk types (`assumption`, `interaction`, `lookup`, `table`, `standard_section`) normalize at compile time via `engine/reference/node_types.py`.

Authoring templates: [`quantity.md`](../node-templates/quantity.md), [`designation.md`](../node-templates/designation.md), [`embedded_source.md`](../node-templates/embedded_source.md).

## Implicit ports (current)

Dataflow is expressed today via:

- Parameter: `input_id` (task key) + `symbol` (equation variable)
- Equation: `requires` / `calculates` / `keys` lists
- Runtime: flat `task.inputs` / `task.outputs`

Future work may add explicit `ports` and `connections` blocks; the compile layer can lower legacy fields automatically.

## Unit graph

Units are **first-class graph nodes** in `standards/units/`, not inline strings on parameters.

```
parameter.canonical_unit  →  UNIT-Pa
UNIT-psi  --converts_to-->  UNIT-Pa  { factor: 6894.757... }
```

Runtime conversion walks `converts_to` edges (BFS) via `engine/units/unit_resolver.py`. `engine/executor/unit_manager.py` delegates to the resolver with a legacy constant fallback.

Parameters declare:

```yaml
canonical_unit: UNIT-Pa
```

The compile step sets `unit` (display symbol) from the canonical unit node for backward compatibility.

## Semantic edges

| Edge | Purpose |
|------|---------|
| `requires`, `calculates` | Equation dataflow (being superseded by port model long-term) |
| `contains`, `anchors_to`, `defines`, `explains` | Structure and navigation |
| `next_step` + `when` | Conditional branching / lazy expansion |
| `converts_to` | Unit conversion (factor, optional offset) |
| `accepts` | Parameter accepts alternate unit nodes |

## Extension points

- **Node behavior registry** (`engine/graph/node_behaviors.py`): `(type, kind)` predicates for expansion, execution, display
- **Display metadata** (optional YAML `display:` block): Dev Studio and Graph Explorer styling
- **Workflow navigation** (`navigation:` on workflow nodes): phased field order for parameter gathering
- **Dev Studio** (`api/dev_studio/`): authoring API and schemas — see [`docs/node_dev_studio.md`](../node_dev_studio.md)

### Workflow navigation metadata

Workflow nodes may declare phased input collection:

```yaml
navigation:
  assumption_gate_fields:
    - straight_pipe_section
    - pressure_loading
  phases:
    expansion_assumptions: [straight_pipe_section]
    path_decisions: [pressure_loading]
    parameter_gathering: [design_pressure, outside_diameter, ...]
```

Loaded via `engine/graph/workflow_navigation.py`. Legacy hardcoded phase lists in `navigation_phases.py` fall back when metadata is absent.

## Graph traversal

When a compiled graph cache exists (`GraphStore.available`), `GraphEngine.build_plan` uses the micro-graph only. Set `VER03_LEGACY_GRAPH_TRAVERSAL=1` to allow legacy `depends_on` traversal for unmigrated workflows.

## Phase 3 — relationship metadata

Equations and lookups `require` **quantity** or **designation** nodes directly. Relationship metadata on each `requires` entry supplies the sympy `alias`, human `role`, and `displayName`. The engine resolves concept nodes to task-bound `parameter` nodes via `references` edges (`engine/graph/relationship_resolver.py`).

One quantity node (e.g. `B313-quantity-pressure`) may appear in multiple equations with different aliases (`P` internal, `Pe` external) without duplicating graph knowledge.

## Phase 4 — Workflow State API

- `TaskStateManager.get_workflow_state()` builds a serializable snapshot from `Task`
- `task_state` API responses include a `workflow_state` object (additive; existing `inputs`/`outputs` unchanged)
- `GET /api/v1/tasks/{task_id}/workflow-state` returns the snapshot only

## Phase 5 — Workflow parameters

`WorkflowState.parameters` maps task keys to `WorkflowParameter` records:

| Field | Source |
|-------|--------|
| `name` | Task `input_id` / output key |
| `value` | `Task.inputs` or `Task.outputs` |
| `dimension` | Linked `quantity` node via parameter `references` edge |
| `unit` | Engineering input or `{key}_unit` output |
| `priority` | `parameter_collection_priority` on active path |
| `source` | `user_input`, `lookup`, `equation`, `default`, or `derived` |
| `status` | Input status or `confirmed` for outputs |
| `concept_id` | Quantity or designation node id |

Designation-linked parameters have `dimension=None`. Execution still mutates `Task` directly; reports still read `Task` (Phase 13).

## Phase 6 — Unit System

Units are separated from quantities. The **Unit Registry** ([`engine/units/unit_registry.py`](../../engine/units/unit_registry.py)) indexes the global unit pack by dimension and resolves allowed units for parameters.

| Field | Source |
|-------|--------|
| `canonical_unit` | Parameter node `canonical_unit` (`UNIT-*`) |
| `allowed_units` | Explicit `allowed_units` on parameter, else all units for linked quantity `dimension` |
| `unit_id` | Resolved runtime unit (`UNIT-*`) from task input / output unit string |

**Dimension aliases** (quantity dimension → registry dimension):

| Quantity dimension | Registry dimension |
|--------------------|--------------------|
| `stress` | `pressure` (Pa, psi, bar, MPa) |

**Designations** (NPS, material grade, joint category) never receive dimensional unit lists — only `UNIT-dimensionless`.

Quantities declare `dimension` only (no units). Parameters bind units via `canonical_unit`. Legacy inline `allowed_units` in section `node.md` files remain for unmigrated paths; micro-graph validation uses [`validate_task_input_units`](../../engine/validation/unit_validator.py).

## Phase 7 — Documentation Fields

Structured documentation is resolved by [`engine/graph/documentation_resolver.py`](../../engine/graph/documentation_resolver.py) into [`NodeDocumentation`](../../models/node_documentation.py).

| Field | YAML (camelCase ok) | Legacy source |
|-------|---------------------|---------------|
| `title` | `title` | `title`, `name` |
| `summary` | `summary` | `summary`, `purpose` |
| `description` | `description` | `description`, markdown body |
| `before_enter` | `beforeEnter` | explicit only |
| `after_exit` | `afterExit` | explicit only |
| `instructions` | `instructions` | `instructions`, `question` |
| `warnings` | `warnings` | list |
| `tips` | `tips` | list |
| `references` | `references` | `references`, `defined_in` |
| `report_summary` | `reportSummary` | explicit only |

Template substitution (`{{design_pressure}}`, `{{P}}`) uses [`engine/graph/doc_templates.py`](../../engine/graph/doc_templates.py) with task/runtime context.

`WorkflowState` (version `"3"` when docs resolved):

| Field | Content |
|-------|---------|
| `current_documentation` | Active step documentation |
| `node_documentation` | Map for visited nodes + workflow root |

[`display_emitter.py`](../../engine/graph/display_emitter.py) prefers resolved docs with legacy fallback. Pilot migration: pipe-wall workflow root, `B313-param-P`, initiation text, `B313-eq-wall-thickness`. Authoring: [`documentation.md`](../node-templates/documentation.md).

## Phase 8 — Execution Engine Lifecycle Events

The executor ([`engine/executor/executor.py`](../../engine/executor/executor.py)) emits graph lifecycle events via [`WorkflowLifecycleEmitter`](../../engine/execution/lifecycle_emitter.py) during plan traversal. These are **distinct** from audit [`EventType`](../../models/event.py) events (`CALCULATION_STARTED`, etc.) on [`EventLogger`](../../engine/events/event_logger.py).

| Lifecycle event | When emitted |
|-----------------|--------------|
| `beforeEnter` | After node validation passes; message from `NodeDocumentation.before_enter` |
| `onEnter` | Immediately after `beforeEnter` |
| `onExecute` | Before `NodeRunner.run` for executable equation/lookup nodes |
| `onExit` | After successful `COMPLETED` execution |
| `onError` | After `ERROR` execution status |

Persisted on task as `_lifecycle_events`. Exposed on `WorkflowState.execution_events` (version `"4"` when present).

`beforeEnter` / `onExit` link to Phase 7 documentation fields. Presentation (Phase 9) consumes these events without coupling execution to UI.

## Phase 9 — Presentation Engine

[`engine/presentation/presentation_engine.py`](../../engine/presentation/presentation_engine.py) builds ordered `presentation_blocks` from **Knowledge Graph + WorkflowState only** (no direct `Task` reads). Wired in [`engine/state/workflow_state.py`](../../engine/state/workflow_state.py) when a `StandardsReader` is available.

| Block type | Source |
|------------|--------|
| `paragraph` | `node_documentation`, `current_documentation`, lifecycle `beforeEnter` |
| `parameter_request` | `parameters` with `pending` / `proposed_default` status |
| `warning` | `workflow_state.warnings` |
| `lookup_result` | `lookup_results` |
| `symbol_table`, `equation_result` | Visited equation nodes via [`display_emitter.py`](../../engine/graph/display_emitter.py) |

Exposed on `WorkflowState.presentation_blocks` (version `"5"` when non-empty). Serialized through existing `workflow_state` API payloads.

Legacy desktop rendering still uses `display_outputs` from [`api/output_blocks.py`](../../api/output_blocks.py). A future cutover can map `presentation_blocks` to desktop block types without changing execution.

## Phase 10 — Equation Renderer

[`engine/equation/equation_renderer.py`](../../engine/equation/equation_renderer.py) produces four SymPy-based display steps for each evaluated equation:

| Step | Meaning |
|------|---------|
| `original` | Authored `display_latex` (or `sympy` expression) |
| `substituted` | RHS after symbolic `.subs()` with numeric values |
| `simplified` | `.simplify()` of the substituted expression |
| `evaluated` | Final numeric result (`lhs = value`) |

[`evaluate_equation()`](../../engine/equation/sympy_evaluator.py) calls the renderer (no regex string replacement). `EquationEvalResult.render_steps` is persisted on execution trace as `render_steps` and exposed on `equation_result` presentation blocks as `steps`. The legacy `substitution` string (`substituted → evaluated`) is retained for older consumers.

## Phase 11 — Node Outputs

Every executable node exposes structured outputs on `WorkflowState.node_outputs`, keyed by producing `node_id`. Built by [`engine/state/node_outputs.py`](../../engine/state/node_outputs.py) from execution history, graph `calculates` / `output_param` metadata, task lookup payloads, designation-linked selections, and workflow completion.

| Node kind | Example output |
|-----------|----------------|
| Equation | Required thickness (`calculates` parameter nodes) |
| Lookup | Allowable stress, outside diameter, wall thickness |
| Selection | Material (designation-linked confirmed user input) |
| Workflow | `Completed Task` + `goal_output` when task status is `COMPLETED` |

Version `"6"` when `node_outputs` is non-empty. Outputs feed downstream execution via existing `task.inputs` / `task.outputs`; this phase formalizes the catalog on `WorkflowState` without changing the executor boundary.

## Content audit (B31.3 micro-graph)

| `type` | Notes |
|--------|-------|
| `definition` | Section anchors (e.g. `B313-304.1.1`); child assumptions, interactions, equations, texts embedded in `node.yaml` |
| `calculation` | Executable sections (e.g. `B313-304.1.2`); embedded equations, conditions, notes |
| `parameter` | Includes `kind: assumption` and `kind: interaction` (embedded or standalone) |
| `equation` | Sympy calculations and `kind: lookup`; often embedded under parent `equations:` with `source:` |
| `quantity` | Shared catalog (pressure, diameter, stress, temperature, thickness) |
| `designation` | NPS, material grade, joint category |
| `workflow` | Pipe wall + MAWP |
| `text` | Initiation, equation intros, notes (`texts:` container on parents) |

- Section nodes use single-file authoring: `node.yaml` (structure + paragraph trace).
- Embedded `source:` blocks are the preferred child-node form; legacy `equations/*.md` files remain as `file:` aliases.
- No `value`, `user_input`, or `runtime_unit` fields in YAML node sources.

## Related docs

- [`docs/node-templates/`](../node-templates/) — authoring templates
- [`AGENTS.md`](../../AGENTS.md) — agent workflow and test commands
