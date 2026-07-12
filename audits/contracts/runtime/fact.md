# Fact Runtime Contract

## Purpose

A **Fact** stores an actual engineering value at runtime — what the user entered, what a lookup returned, or what an equation calculated. Facts instantiate immutable **Parameter** nodes (`PARAM-*`) from the knowledge graph with concrete values and full traceability.

Facts answer: *"What value is known right now for this parameter?"*

## What it is

| Aspect | Detail |
| --- | --- |
| **Layer** | Runtime model on `Task` |
| **Storage** | `Task.execution_context.fact_store` ([`models/fact_store.py`](../../../models/fact_store.py)) |
| **Type** | `type: fact` |
| **Mutable** | Yes — but **append-only** (corrections create new Facts; old ones are superseded) |
| **Authored in `knowledge/`?** | **No** — Facts are created during execution, not as YAML nodes |

```text
Parameter (knowledge):  PARAM-design-pressure  →  defines meaning
Fact (runtime):         design_pressure = 8 bar  →  stores the value
```

### Conceptual rule

```text
Parameter defines what the value means.
Fact records what value is known.
Provenance explains where the value came from.
Supersession preserves history.
```

## Key fields

### Required top-level fields

| Field | Purpose |
| --- | --- |
| `id` | Runtime identity (e.g. `FACT-design-pressure-001`) |
| `type` | Must be `fact` |
| `parameter` | `PARAM-*` node this Fact instantiates |
| `key` | Runtime field key (usually matches Parameter `key`) |
| `fact_class` | How the Fact was created (see enums below) |
| `source` | Origin of the value (user, lookup, equation, etc.) |
| `provenance` | Execution trace (task, workflow, goal, timestamp) |
| `validation` | Validation status and unit checks |
| `supersession` | Append-only correction tracking |

### Value shapes (by Parameter class)

**Numeric** — pressures, temperatures, lengths, stresses:

```yaml
value:
  amount: 8
  unit: UNIT-bar
canonical_value:
  amount: 800000
  unit: UNIT-Pa
```

**Categorical** — material specs, joint categories, schedules:

```yaml
value:
  label: ASTM A106 Grade B
  normalized_key: astm_a106_grade_b
```

**Boolean** — yes/no assumptions and confirmations:

```yaml
value:
  boolean: true
```

**Structured** — only when a scalar cannot represent the value safely:

```yaml
value:
  object:
    material_standard: ASTM A106
    grade: B
```

### `fact_class` values

```text
user_supplied, calculated, looked_up, imported, default_confirmed,
assumed, validated, derived, system_generated
```

### `source` model

| `source_type` | When used |
| --- | --- |
| `user_input` | User supplied during input collection |
| `table_lookup` | Retrieved from a standards table (`lookup_node`, `source_id`) |
| `equation` | Produced by an equation (`source_id`, `input_facts`) |
| `validation_rule` | Result of a validation check |
| `default_confirmed` | User accepted a graph default |
| `system` / `import` | System-generated or imported values |

### `provenance` fields

| Field | Purpose |
| --- | --- |
| `execution_context_id` | Parent execution context |
| `task_id` | User task |
| `project_id` | Persistent project (if applicable) |
| `workflow_id` | Active workflow |
| `goal_id` | Goal this Fact helps satisfy |
| `created_by` | `user`, `planner`, `kernel`, `lookup`, etc. |
| `collected_at_node` / `produced_by_node` | Graph node where value was gathered or produced |
| `collected_at_phase` | Workflow phase (e.g. `parameter_gathering`) |
| `timestamp` | Creation time (ISO 8601) |

### `validation` statuses

```text
pending, confirmed, validated, rejected, superseded, conflicting
```

Typical shape:

```yaml
validation:
  status: confirmed
  unit_validated: true
  dimension: DIM-pressure
  warnings: []
  errors: []
```

### Append-only supersession

Do **not** edit an existing Fact when a value changes. Create a new Fact and link supersession:

```yaml
# New Fact (active)
supersession:
  supersedes: FACT-design-temperature-001
  superseded_by: null
  active: true
  reason: User corrected design temperature.

# Old Fact (inactive)
supersession:
  supersedes: null
  superseded_by: FACT-design-temperature-002
  active: false
```

## Relationships

Facts connect to knowledge nodes and other runtime objects conceptually (and optionally via `edges`):

| Relationship | Target | Meaning |
| --- | --- | --- |
| `instantiates` | `PARAM-*` | Fact holds a value for this Parameter |
| `satisfies_goal` | `GOAL-*` | Fact completes a Goal |
| `produced_by` | `EQ-*`, `LOOKUP-*`, paragraph id | Source node that produced the Fact |
| `derived_from` / input via `source.input_facts` | `FACT-*` | Upstream Facts used to compute this one |
| `validated_by` | `VALRULE-*` | Validation rule that checked this Fact |
| `supersedes` | `FACT-*` | Correction chain |
| `conflicts_with` | `FACT-*` | Unresolved conflicting value |
| `belongs_to_execution_context` | `EXEC-*` | Parent context |

Related runtime contracts:

- [Goal](goal.md) — objectives Facts satisfy
- [Execution Context](execution-context.md) — container holding `fact_store`

## What NOT to put here

Facts must **not** define engineering meaning. Forbidden content belongs on immutable knowledge nodes:

```text
concept_definition, dimension_definition, unit_conversion_rule,
parameter_aliases, equation_formula, standard_text, workflow_definition
```

### Invalid Fact conditions

1. `type` is not `fact`
2. `parameter` does not reference a valid `PARAM-*` node
3. Value type incompatible with Parameter class
4. Numeric Fact uses a unit not allowed by the Parameter dimension
5. Numeric Fact missing `canonical_value`
6. Derived Fact missing `source.input_facts`
7. Lookup Fact missing table/lookup provenance
8. User-supplied Fact missing user/input provenance
9. In-place edit instead of supersession
10. Fact redefines Parameter meaning

## Implementation reference

| Module | Role |
| --- | --- |
| [`models/fact.py`](../../../models/fact.py) | `Fact` dataclass, enums (`FactClass`, `ValidationStatus`, `SourceType`), value types, serialization |
| [`models/fact_store.py`](../../../models/fact_store.py) | Append-only store on `ExecutionContext`; active-by-key lookup and supersession |
| [`models/execution_context.py`](../../../models/execution_context.py) | Hosts `fact_store` and `facts_index` (active / superseded / conflicting id lists) |

**On Task:** `task.execution_context.fact_store` holds all Facts for the current execution.

**Migration note:** Consolidated from former `docs/node-templates/` runtime templates (removed).
