# Execution Context Runtime Contract

## Purpose

An **Execution Context** is the mutable runtime container for one engineering execution. It holds everything that changes while a task runs: active Goals, known Facts, user decisions, assumptions, validation findings, blocked state, and execution event references.

It answers: *"What is currently happening in this engineering execution?"*

## What it is

| Aspect | Detail |
| --- | --- |
| **Layer** | Runtime model on `Task` |
| **Storage** | `Task.execution_context` ([`models/execution_context.py`](../../../models/execution_context.py)) |
| **Type** | `type: execution_context` |
| **Mutable** | Yes — updated continuously by Planner and Kernel |
| **Authored in `knowledge/`?** | **No** — created per task/workflow run |

```text
Execution Context  →  what happened and what is in progress
Knowledge graph    →  what the system knows independently of any run
```

### Conceptual rule

```text
The Execution Context stores what happened.
Goals store what was desired.
Facts store what became known.
Events store the execution history.
Knowledge nodes define what the system knows independently of execution.
```

### Planner / Kernel boundary

| Component | May do |
| --- | --- |
| **Planner** | Create Goals, expand goal trees, identify missing Parameters, request user input, suggest next steps |
| **Kernel** | Create Facts, mark Goals complete, update execution state, schedule execution, record events, detect blocked execution |

The Execution Context is where both communicate through structured runtime state.

## Key fields

### Required top-level fields

| Field | Purpose |
| --- | --- |
| `id` | Runtime identity (e.g. `EXEC-2026-000001`) |
| `type` | Must be `execution_context` |
| `task_id` | Task this context belongs to |
| `workflow_id` | Workflow being executed |
| `status` | Current execution lifecycle state |
| `authority_context_id` | Link to active [Authority Context](authority-context.md) |
| `active_goals` | Goal ids currently being pursued |
| `fact_store` | All Facts (see [Fact contract](fact.md)) |
| `goal_store` | All Goals (see [Goal contract](goal.md)) |
| `facts_index` | Active / superseded / conflicting Fact id lists |
| `state` | Phase, blocked parameters, ready/blocked/completed Goals |
| `execution_trace` | References to execution events |
| `metadata` | Created/modified timestamps, version |

### Optional fields

| Field | Purpose |
| --- | --- |
| `project_id` | Persistent project scope |
| `decisions` | Explicit runtime branch choices |
| `assumptions` | Accepted claims affecting expansion |
| `validation` | Runtime validation summary |
| `warnings` | Non-fatal execution warnings |
| `conflicts` | Input conflicts requiring replan |

### `status` values

```text
new, active, awaiting_input, ready, executing, blocked,
completed, invalidated, failed, paused, cancelled, in_progress
```

### `state` model

Describes what the system is waiting for — it records status; it does not define engineering meaning:

```yaml
state:
  current_phase: parameter_gathering
  blocked_by:
    - PARAM-outside-diameter
  ready_goals:
    - GOAL-allowable-stress-001
  blocked_goals:
    - GOAL-required-wall-thickness-001
  completed_goals:
    - GOAL-resolve-design-pressure-001
```

### `facts_index` model

Groups Fact ids by runtime acceptance status (full Fact objects live in `fact_store`):

```yaml
facts_index:
  active:
    - FACT-design-pressure-001
  superseded:
    - FACT-design-pressure-000
  conflicting:
    - FACT-design-pressure-002
```

- **Active** — currently accepted for execution
- **Superseded** — preserved for traceability after correction
- **Conflicting** — retained until authority, validation, or user resolves them

### `decisions` model

Records explicit runtime choices that affect engineering outcome:

```yaml
decisions:
  - id: DECISION-pressure-loading-001
    parameter: PARAM-pressure-loading
    selected_value: internal_pressure
    source: user_input
    reason: User selected internal pressure design path.
    timestamp: 2026-07-02T10:20:00Z
```

Examples: internal vs external pressure, straight pipe vs fitting, NPS lookup vs direct OD, branch selection.

### `assumptions` model

Runtime claims accepted for execution (may later become Facts):

```yaml
assumptions:
  - id: ASSUMPTION-straight-pipe-section-001
    parameter: PARAM-straight-pipe-section
    value: true
    confirmed_by: user
    affects_expansion: true
    timestamp: 2026-07-02T10:19:00Z
```

### `validation` model

Runtime-specific validation results (knowledge graph defines rules; context records outcomes):

```yaml
validation:
  status: pass_with_warning   # e.g. incomplete, pass, pass_with_warning
  warnings:
    - WARN-temperature-range-001
  errors: []
  overrides:
    - OVERRIDE-temperature-limit-001
```

### `execution_trace` model

References event ids created during execution (detailed records may live in the Event Logger):

```yaml
execution_trace:
  events:
    - EVENT-task-created-001
    - EVENT-goal-expanded-001
    - EVENT-fact-created-001
    - EVENT-calculation-completed-001
```

## Relationships

```text
Execution Context
  ├── contains Goals        → goal_store ([Goal contract](goal.md))
  ├── contains Facts        → fact_store ([Fact contract](fact.md))
  ├── references Authority  → authority_context_id ([Authority Context](authority-context.md))
  ├── records Decisions     → decisions[]
  ├── records Assumptions   → assumptions[]
  ├── records Validation    → validation{}
  └── references Events     → execution_trace.events[]
```

| Peer / child | Link field | Role |
| --- | --- | --- |
| [Authority Context](authority-context.md) | `authority_context_id` | Governing standards for this run |
| [Goal](goal.md) | `goal_store`, `active_goals`, `state.*_goals` | Objectives and progress |
| [Fact](fact.md) | `fact_store`, `facts_index` | Known values |
| Task | `task_id` | Parent user task |
| Workflow | `workflow_id` | Active workflow definition (`WF-*` in knowledge) |

## What NOT to put here

The Execution Context must **not** define immutable knowledge:

```text
parameter_definition, concept_definition, dimension_definition,
unit_conversion_rule, equation_formula_definition, standard_paragraph_text,
authority_text, workflow_definition
```

Those belong in `knowledge/` or the authority graph.

### Invalid Execution Context conditions

1. `type` is not `execution_context`
2. Missing `task_id`
3. Missing `workflow_id` (unless free-form exploratory context)
4. References Facts not belonging to this context or project
5. Marks a Goal complete without a satisfying Fact or accepted terminal status
6. Contains mutable edits to immutable knowledge nodes
7. Reports `status: completed` with active conflicts
8. Reports `status: completed` with blocked Goals
9. Lacks Authority Context for standards-governed execution
10. Loses superseded Facts (append-only history required)

## Implementation reference

| Module | Role |
| --- | --- |
| [`models/execution_context.py`](../../../models/execution_context.py) | `ExecutionContext` dataclass, status enums, nested state/decision/assumption types |
| [`models/fact_store.py`](../../../models/fact_store.py) | `ExecutionContext.fact_store` |
| [`models/goal_store.py`](../../../models/goal_store.py) | `ExecutionContext.goal_store` |
| [`models/task.py`](../../../models/task.py) | Each `Task` owns one `execution_context` and one `authority_context` |

**On Task:** `task.execution_context` is the primary mutable execution state for API, planner, and kernel layers.

**Linked peer:** `task.authority_context` via `execution_context.authority_context_id` ↔ `authority_context.execution_context_id` — see [Authority Context](authority-context.md).

**Migration note:** Consolidated from former `docs/node-templates/` runtime templates (removed).
