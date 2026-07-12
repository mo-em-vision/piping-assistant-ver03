# Goal Runtime Contract

## Purpose

A **Goal** represents a runtime engineering objective the system must achieve — calculate a thickness, resolve a lookup, verify a rule, or collect missing input. Goals do **not** contain answers; they are satisfied when the required output **Fact** exists and passes validation.

Goals answer: *"What is the system trying to achieve next?"*

## What it is

| Aspect | Detail |
| --- | --- |
| **Layer** | Runtime model on `Task` |
| **Storage** | `Task.execution_context.goal_store` ([`models/goal_store.py`](../../../models/goal_store.py)) |
| **Type** | `type: goal` |
| **Mutable** | Yes — Planner expands trees; Kernel updates satisfaction and state |
| **Authored in `knowledge/`?** | **No** — Goals are created during planning and execution |

```text
Goal:     Determine required wall thickness   (objective)
Fact:     required_wall_thickness = 4.82 mm  (proof the Goal is satisfied)
```

### Conceptual rule

```text
Goal defines what is desired.
Parameter defines what kind of result is desired.
Fact proves that the Goal has been satisfied.
Planner expands Goals.
Kernel executes ready Goals.
```

### Planner / Kernel boundary

| Component | May do |
| --- | --- |
| **Planner** | Create Goals, expand goal trees, identify missing Facts, rank paths, request user input |
| **Kernel** | Execute ready Goals, mark blocked/satisfied, record produced Facts, update execution state |

The Goal object itself does not perform execution.

## Key fields

### Required top-level fields

| Field | Purpose |
| --- | --- |
| `id` | Runtime identity (e.g. `GOAL-required-wall-thickness-001`) |
| `type` | Must be `goal` |
| `key` | Machine-safe goal key |
| `name` | Human-readable goal name |
| `goal_class` | Type of objective (see enums below) |
| `target_parameter` | `PARAM-*` the Goal produces, verifies, or resolves |
| `satisfaction` | Completion condition and status |
| `provenance` | Runtime origin (task, workflow, planner, timestamp) |
| `state` | Current runtime state (blocked, active, child/parent links) |

### Optional fields

| Field | Purpose |
| --- | --- |
| `required_facts` | List of `{ parameter: PARAM-* }` prerequisites |
| `question` | For `input_goal` — prompt metadata (`prompt`, `reason`, `expected_value_class`) |
| `authority` | Paragraph references governing this Goal (`references: [...]`) |
| `edges` | Typed relationships to Parameters, Facts, workflows |
| `metadata` | Version and extension fields |

### `goal_class` values

```text
calculation_goal   — compute a numeric or derived value
lookup_goal        — retrieve from table or authority source
validation_goal    — verify a condition or rule passes
selection_goal     — choose among valid engineering options
verification_goal  — determine acceptability / compliance
report_goal        — generate structured output
input_goal         — obtain a missing Fact from user
decision_goal      — record an explicit branch choice
explanation_goal   — produce traversal or guidance narration
```

### Satisfaction model

A Goal is complete when its required output Fact exists and passes validation:

```yaml
satisfaction:
  status: satisfied
  satisfied_by: FACT-required-wall-thickness-001
  required_output:
    parameter: PARAM-required-wall-thickness
  validation_status: validated
```

**`satisfaction.status` values:**

```text
pending, ready, blocked, executing, satisfied, failed, deferred, superseded
```

### State model (runtime-only)

```yaml
state:
  status: blocked
  blocked_by:
    - PARAM-design-pressure
    - PARAM-material-specification
  child_goals:
    - GOAL-resolve-design-pressure
  parent_goal: GOAL-verify-pipe-wall-thickness
```

**`state.status` values:**

```text
active, blocked, ready, executing, satisfied, failed, deferred, superseded
```

### Goal tree

Goals may form parent/child trees. The Planner expands subtrees; the Kernel executes leaves when ready:

```text
GOAL-verify-pipe-wall-thickness
  ├── GOAL-resolve-design-pressure
  ├── GOAL-resolve-allowable-stress
  ├── GOAL-calculate-required-wall-thickness
  └── GOAL-check-thin-wall-applicability
```

`GoalStore.link_child()` enforces acyclic parent/child relationships (`GoalCycleError` on cycles).

## Relationships

| Relationship | Target | Meaning |
| --- | --- | --- |
| `requires_fact` | `PARAM-*` | Prerequisite parameter must have an active Fact |
| `satisfied_by` | `FACT-*` | Fact that completed this Goal |
| `expands_to` / `child_goal` | `GOAL-*` | Child objectives |
| `parent_goal` | `GOAL-*` | Parent objective |
| `blocked_by` | `PARAM-*` | Missing inputs blocking progress |
| `created_from_workflow` | `WF-*` | Originating workflow |
| `governed_by` | paragraph id | Governing standard paragraph |
| `executed_by` | kernel / planner actor | Who last advanced the Goal |
| `produced_fact` | `FACT-*` | Output Fact from execution |
| `failed_because` | reason / node | Failure attribution |
| `superseded_by` | `GOAL-*` | Replaced objective |

Related runtime contracts:

- [Fact](fact.md) — values that satisfy Goals
- [Execution Context](execution-context.md) — container holding `goal_store` and phase state
- [Authority Context](authority-context.md) — governing sources when authority is required

## What NOT to put here

Goals must **not** store engineering definitions or computed results:

```text
formula, calculation_result, numeric_result, unit_conversion_rule,
standard_text, parameter_definition, concept_definition
```

Those belong on Equations, Facts, Units, Paragraphs, Parameters, or Concepts in `knowledge/`.

### Invalid Goal conditions

1. `type` is not `goal`
2. `goal_class` is missing
3. No `target_parameter` (except pure report/explanation Goals)
4. Marked satisfied without a valid Fact or accepted terminal state
5. Stores a calculated value directly (belongs on a Fact)
6. Modifies immutable knowledge
7. Cyclic parent/child relationships
8. Missing provenance
9. Bypasses [Authority Context](authority-context.md) when authority is required
10. Marked complete while required child Goals remain unresolved

## Implementation reference

| Module | Role |
| --- | --- |
| [`models/goal.py`](../../../models/goal.py) | `Goal` dataclass, enums (`GoalClass`, `SatisfactionStatus`, `GoalRuntimeStatus`), serialization |
| [`models/goal_store.py`](../../../models/goal_store.py) | Goal tree store on `ExecutionContext`; root tracking, child linking, cycle detection |
| [`models/execution_context.py`](../../../models/execution_context.py) | Hosts `goal_store`; `state.ready_goals`, `blocked_goals`, `completed_goals` |

**On Task:** `task.execution_context.goal_store` holds all Goals for the current execution.

**Migration note:** Consolidated from former `docs/node-templates/` runtime templates (removed).
