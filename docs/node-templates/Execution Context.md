# Execution Context Template

> **Implementation:** [`models/execution_context.py`](../../models/execution_context.py) on each `Task` as `execution_context`. References [`Authority Context`](Authority%20Context.md) via `authority_context_id`. Not a knowledge-graph node type.

An Execution Context is the runtime container for one engineering execution.

It contains the active Goals, Facts, decisions, assumptions, validation results, execution history, and warnings for a specific task or workflow run.

An Execution Context is mutable.  
It is not part of the immutable knowledge graph.

```yaml
---
id: EXEC-2026-000001
type: execution_context

task_id: TASK-pipe-wall-thickness-001
project_id: PROJECT-refinery-line-12
workflow_id: WF-pipe-wall-thickness-design

status: active

authority_context: AUTHCTX-2026-000001

active_goals:
  - GOAL-required-wall-thickness-001
  - GOAL-allowable-stress-001

facts:
  active:
    - FACT-design-pressure-001
    - FACT-material-specification-001
    - FACT-design-temperature-001

  superseded: []

  conflicting: []

state:
  current_phase: parameter_gathering
  blocked_by:
    - PARAM-outside-diameter
    - PARAM-corrosion-allowance

  ready_goals: []
  blocked_goals:
    - GOAL-required-wall-thickness-001

  completed_goals: []

decisions:
  - id: DECISION-pressure-loading-001
    parameter: PARAM-pressure-loading
    selected_value: internal_pressure
    source: user_input
    timestamp: 2026-07-02T10:20:00Z

assumptions:
  - id: ASSUMPTION-straight-pipe-section-001
    parameter: PARAM-straight-pipe-section
    value: true
    confirmed_by: user
    timestamp: 2026-07-02T10:19:00Z

validation:
  status: incomplete
  warnings: []
  errors: []
  overrides: []

execution_trace:
  events:
    - EVENT-task-created-001
    - EVENT-goal-created-001
    - EVENT-input-received-001

metadata:
  created: 2026-07-02T10:18:00Z
  modified: 2026-07-02T10:30:00Z
  version: 1
---
```

---

# Purpose

The Execution Context answers:

```text
What is currently happening in this engineering execution?
```

It is the runtime container for:

```text
Goals
Facts
Decisions
Assumptions
Warnings
Validation findings
Execution events
Current phase
Blocked state
```

It is the place where mutable execution state lives.

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Runtime execution context identity.|
|`type`|Must be `execution_context`.|
|`task_id`|Task this context belongs to.|
|`workflow_id`|Workflow being executed.|
|`status`|Current execution state.|
|`authority_context`|Active governing authority context.|
|`active_goals`|Goals currently being pursued.|
|`facts`|Runtime facts known in this execution.|
|`state`|Current execution state.|
|`execution_trace`|Event history.|
|`metadata`|Runtime timestamps/versioning.|

---

# Status values

Recommended values:

```yaml
new
active
awaiting_input
ready
executing
blocked
completed
invalidated
failed
paused
cancelled
```

---

# State model

The `state` section describes what the system is waiting for.

```yaml
state:
  current_phase: parameter_gathering

  blocked_by:
    - PARAM-outside-diameter
    - PARAM-corrosion-allowance

  ready_goals:
    - GOAL-allowable-stress-001

  blocked_goals:
    - GOAL-required-wall-thickness-001

  completed_goals:
    - GOAL-resolve-design-pressure-001
```

The Execution Context does not decide engineering meaning.  
It only records runtime status.

---

# Facts model

Facts are grouped by runtime status.

```yaml
facts:
  active:
    - FACT-design-pressure-001

  superseded:
    - FACT-design-pressure-000

  conflicting:
    - FACT-design-pressure-002
```

Active Facts are the currently accepted Facts for execution.

Superseded Facts are preserved for traceability.

Conflicting Facts are retained until authority, validation, or user decision resolves them.

---

# Decisions model

Decisions record explicit runtime choices.

```yaml
decisions:
  - id: DECISION-pressure-loading-001
    parameter: PARAM-pressure-loading
    selected_value: internal_pressure
    source: user_input
    reason: User selected internal pressure design path.
    timestamp: 2026-07-02T10:20:00Z
```

Examples:

```text
internal vs external pressure
straight pipe vs fitting
NPS lookup vs direct outside diameter
default coefficient accepted vs overridden
thin-wall branch vs thick-wall branch
```

Decisions should be reportable when they affect engineering outcome.

---

# Assumptions model

Assumptions are runtime claims accepted for execution.

```yaml
assumptions:
  - id: ASSUMPTION-straight-pipe-section-001
    parameter: PARAM-straight-pipe-section
    value: true
    confirmed_by: user
    affects_expansion: true
    timestamp: 2026-07-02T10:19:00Z
```

Assumptions may later become Facts if they instantiate Parameters.

---

# Validation model

```yaml
validation:
  status: pass_with_warning
  warnings:
    - WARN-temperature-range-001
  errors: []
  overrides:
    - OVERRIDE-temperature-limit-001
```

Validation belongs in the Execution Context because it is runtime-specific.

The immutable knowledge graph defines possible rules.  
The Execution Context records what happened in this execution.

---

# Execution trace

The Execution Context references all events created during execution.

```yaml
execution_trace:
  events:
    - EVENT-task-created-001
    - EVENT-goal-expanded-001
    - EVENT-input-requested-001
    - EVENT-fact-created-001
    - EVENT-validation-warning-001
    - EVENT-calculation-completed-001
```

The Event Logger may store the detailed event records separately.

The Execution Context should reference them.

---

# Example: completed execution context

```yaml
---
id: EXEC-2026-000001
type: execution_context

task_id: TASK-pipe-wall-thickness-001
project_id: PROJECT-refinery-line-12
workflow_id: WF-pipe-wall-thickness-design

status: completed

authority_context: AUTHCTX-2026-000001

active_goals:
  - GOAL-required-wall-thickness-001
  - GOAL-minimum-required-thickness-001

facts:
  active:
    - FACT-design-pressure-001
    - FACT-outside-diameter-001
    - FACT-material-specification-001
    - FACT-design-temperature-001
    - FACT-allowable-stress-001
    - FACT-required-wall-thickness-001
    - FACT-corrosion-allowance-001
    - FACT-minimum-required-thickness-001

  superseded: []

  conflicting: []

state:
  current_phase: completed
  blocked_by: []
  ready_goals: []
  blocked_goals: []
  completed_goals:
    - GOAL-required-wall-thickness-001
    - GOAL-minimum-required-thickness-001

decisions:
  - id: DECISION-pressure-loading-001
    parameter: PARAM-pressure-loading
    selected_value: internal_pressure
    source: user_input

assumptions:
  - id: ASSUMPTION-straight-pipe-section-001
    parameter: PARAM-straight-pipe-section
    value: true
    confirmed_by: user

validation:
  status: pass
  warnings: []
  errors: []
  overrides: []

execution_trace:
  events:
    - EVENT-task-created-001
    - EVENT-goal-created-001
    - EVENT-fact-created-001
    - EVENT-lookup-completed-001
    - EVENT-calculation-completed-001
    - EVENT-report-generated-001

metadata:
  created: 2026-07-02T10:18:00Z
  modified: 2026-07-02T10:40:00Z
  version: 1
---
```

---

# Relationship to other objects

```text
Execution Context
  ├── contains Goals
  ├── contains Facts
  ├── references [Authority Context](Authority%20Context.md)
  ├── records Decisions
  ├── records Assumptions
  ├── records Validation findings
  └── references Events
```

---

# Planner / Kernel boundary

The Planner may:

```text
create Goals
expand Goal trees
identify missing Parameters
request user input
suggest next steps
```

The Kernel may:

```text
create Facts
mark Goals complete
update execution state
schedule execution
record events
detect blocked execution
```

The Execution Context is where both communicate through structured runtime state.

---

# Forbidden fields

Execution Context must not define immutable knowledge.

It must not contain:

```yaml
parameter_definition:
concept_definition:
dimension_definition:
unit_conversion_rule:
equation_formula_definition:
standard_paragraph_text:
authority_text:
workflow_definition:
```

Those belong to the knowledge graph or authority graph.

---

# Validation rules

An Execution Context is invalid if:

1. `type` is not `execution_context`.
    
2. It has no `task_id`.
    
3. It has no `workflow_id`, unless it is a free-form exploratory context.
    
4. It references Facts that do not belong to it or its Project.
    
5. It marks a Goal complete without a satisfying Fact or accepted terminal status.
    
6. It contains mutable edits to immutable knowledge nodes.
    
7. It has active conflicts but reports `status: completed`.
    
8. It has blocked Goals but reports `status: completed`.
    
9. It lacks an Authority Context for standards-governed execution.
    
10. It loses superseded Facts.
    

---

# Conceptual rule

```text
The Execution Context stores what happened.
Goals store what was desired.
Facts store what became known.
Events store the execution history.
Knowledge nodes define what the system knows independently of execution.
```