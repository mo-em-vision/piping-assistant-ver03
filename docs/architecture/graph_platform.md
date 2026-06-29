# Graph Platform Architecture

Ver03 treats engineering standards as a **static micro-graph** compiled from Markdown/YAML sources. Runtime task state holds user values; the graph defines structure, dataflow, and conversion rules.

## Pipeline

```
standards/*/nodes/**/node.yaml  →  GraphBuilder  →  PackGraph  →  optional SQLite cache
                                                              ↓
                                                         GraphStore
                                                              ↓
                                                    MicroGraphEngine / Executor
                                                              ↓
                                                         Task (inputs/outputs)
```

Sources are authoritative. SQLite (`*_graph.db`) is a performance cache only; rebuild with `python scripts/build_graph_db.py`.

## Static vs runtime

| Layer | Owns |
|-------|------|
| **PackGraph** | Node definitions, semantic edges, unit ontology, aliases |
| **Task** | User-entered values, calculation results, workflow progress |
| **ExecutionPlan** | Ordered nodes for one evaluation pass (rebuilt per input set) |

The graph is never mutated during execution.

## Canonical node types

| Type | Role |
|------|------|
| `workflow` | Root orchestration; anchors sections and goal outputs |
| `parameter` | Engineering symbols; `input_id` maps to task state |
| `equation` | Calculations and table lookups (`kind: calculation` or `lookup`) |
| `text` | Sections, tables, explanatory content (`kind: section`, `table`, `content`) |
| `unit` | Global unit ontology (pack: `standards/units/`) |

Legacy on-disk types (`assumption`, `interaction`, `lookup`, `table`, `standard_section`) normalize at compile time via `engine/reference/node_types.py`.

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
- **Dev Studio** (`api/dev_studio/`): authoring API and schemas

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

## Related docs

- [`docs/node-templates/`](../node-templates/) — authoring templates
- [`AGENTS.md`](../../AGENTS.md) — agent workflow and test commands
