# Goal Node

> **Implementation:** [`models/goal.py`](../../models/goal.py) and [`models/goal_store.py`](../../models/goal_store.py) on `Task.execution_context.goal_store`. Not a knowledge-graph node type.

A Goal represents a runtime engineering objective that the system must satisfy.

A Goal is not a knowledge node.  
A Goal belongs to an Execution Context, Task, Workflow run, or Project.

```yaml
---
id: GOAL-required-wall-thickness-001
type: goal

key: required_wall_thickness
name: Determine Required Wall Thickness

goal_class: calculation_goal

target_parameter: PARAM-required-wall-thickness

required_facts:
  - parameter: PARAM-design-pressure
  - parameter: PARAM-outside-diameter
  - parameter: PARAM-material-specification
  - parameter: PARAM-design-temperature
  - parameter: PARAM-allowable-stress
  - parameter: PARAM-weld-joint-efficiency
  - parameter: PARAM-weld-strength-reduction-factor-W
  - parameter: PARAM-temperature-coefficient-Y

satisfaction:
  status: pending
  satisfied_by: null
  required_output:
    parameter: PARAM-required-wall-thickness

provenance:
  execution_context_id: EXEC-2026-000001
  task_id: TASK-pipe-wall-thickness-001
  workflow_id: WF-pipe-wall-thickness-design
  created_from_user_intent: pipe_wall_thickness_design
  created_by: planner
  timestamp: 2026-07-02T10:25:00Z

state:
  status: active
  blocked_by:
    - PARAM-design-pressure
    - PARAM-outside-diameter
    - PARAM-material-specification
  child_goals: []
  parent_goal: null

metadata:
  version: 1
---
```

---

# Purpose

A Goal defines what the system is trying to achieve.

Examples:

```text
Determine required wall thickness.
Resolve allowable stress.
Verify thin-wall applicability.
Select governing equation.
Generate calculation report.
```

A Goal does not contain the final answer.  
A Goal is satisfied when the required output Fact exists and is valid.

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Runtime Goal identity.|
|`type`|Must be `goal`.|
|`key`|Machine-safe goal key.|
|`name`|Human-readable goal name.|
|`goal_class`|Type of goal.|
|`target_parameter`|Parameter the Goal is trying to produce, verify, or resolve.|
|`satisfaction`|Completion condition.|
|`provenance`|Runtime origin.|
|`state`|Current runtime state.|

---

# Recommended `goal_class` values

```yaml
calculation_goal
lookup_goal
validation_goal
selection_goal
verification_goal
report_goal
input_goal
decision_goal
explanation_goal
```

---

# Goal classes

## `calculation_goal`

Used when the system must calculate a value.

```yaml
goal_class: calculation_goal
target_parameter: PARAM-required-wall-thickness
```

Example:

```text
Calculate required wall thickness.
```

---

## `lookup_goal`

Used when the system must retrieve a value from a table or authority source.

```yaml
goal_class: lookup_goal
target_parameter: PARAM-allowable-stress
```

Example:

```text
Resolve allowable stress from material and design temperature.
```

---

## `validation_goal`

Used when the system must verify whether a condition or rule passes.

```yaml
goal_class: validation_goal
target_parameter: PARAM-thin-wall-validity
```

Example:

```text
Verify whether t < D/6.
```

---

## `selection_goal`

Used when the system must choose among valid engineering options.

```yaml
goal_class: selection_goal
target_parameter: PARAM-pressure-loading
```

Example:

```text
Select internal or external pressure design path.
```

---

## `verification_goal`

Used when the system must determine whether a condition is acceptable.

```yaml
goal_class: verification_goal
target_parameter: PARAM-code-compliance-status
```

Example:

```text
Verify whether selected pipe thickness satisfies minimum required thickness.
```

---

## `input_goal`

Used when the system needs a missing Fact.

```yaml
goal_class: input_goal
target_parameter: PARAM-design-pressure
```

Example:

```text
Obtain design pressure from user.
```

---

# Goal tree

Goals may expand into child Goals.

Example:

```text
GOAL-verify-pipe-wall-thickness
  ├── GOAL-resolve-design-pressure
  ├── GOAL-resolve-outside-diameter
  ├── GOAL-resolve-material-specification
  ├── GOAL-resolve-allowable-stress
  ├── GOAL-calculate-required-wall-thickness
  ├── GOAL-check-thin-wall-applicability
  └── GOAL-calculate-minimum-required-thickness
```

The Planner expands the tree.  
The Kernel executes ready Goals.  
Facts satisfy Goals.

---

# Satisfaction model

A Goal is complete when its required output Fact exists and passes validation.

```yaml
satisfaction:
  status: satisfied
  satisfied_by: FACT-required-wall-thickness-001
  required_output:
    parameter: PARAM-required-wall-thickness
  validation_status: validated
```

Recommended statuses:

```yaml
pending
ready
blocked
executing
satisfied
failed
deferred
superseded
```

---

# State model

```yaml
state:
  status: blocked
  blocked_by:
    - PARAM-design-pressure
    - PARAM-material-specification
  child_goals:
    - GOAL-resolve-design-pressure
    - GOAL-resolve-material-specification
  parent_goal: GOAL-verify-pipe-wall-thickness
```

The state field is runtime-only.

---

# Example: allowable stress lookup goal

```yaml
---
id: GOAL-allowable-stress-001
type: goal

key: allowable_stress
name: Resolve Allowable Stress

goal_class: lookup_goal

target_parameter: PARAM-allowable-stress

required_facts:
  - parameter: PARAM-material-specification
  - parameter: PARAM-design-temperature

satisfaction:
  status: pending
  satisfied_by: null
  required_output:
    parameter: PARAM-allowable-stress

provenance:
  execution_context_id: EXEC-2026-000001
  task_id: TASK-pipe-wall-thickness-001
  workflow_id: WF-pipe-wall-thickness-design
  created_by: planner
  timestamp: 2026-07-02T10:26:00Z

state:
  status: blocked
  blocked_by:
    - PARAM-material-specification
    - PARAM-design-temperature
  parent_goal: GOAL-required-wall-thickness-001
  child_goals: []

metadata:
  version: 1
---
```

---

# Example: user input goal

```yaml
---
id: GOAL-design-pressure-input-001
type: goal

key: obtain_design_pressure
name: Obtain Design Pressure

goal_class: input_goal

target_parameter: PARAM-design-pressure

satisfaction:
  status: pending
  satisfied_by: null
  required_output:
    parameter: PARAM-design-pressure

question:
  prompt: >
    Provide the design pressure required for the wall thickness calculation.
  reason: >
    Design pressure is required by the pressure design equation.
  expected_value_class: numeric_with_unit

provenance:
  execution_context_id: EXEC-2026-000001
  task_id: TASK-pipe-wall-thickness-001
  workflow_id: WF-pipe-wall-thickness-design
  created_by: planner
  timestamp: 2026-07-02T10:27:00Z

state:
  status: blocked
  blocked_by: []
  parent_goal: GOAL-required-wall-thickness-001
  child_goals: []

metadata:
  version: 1
---
```

---

# Example: verification goal

```yaml
---
id: GOAL-thin-wall-check-001
type: goal

key: verify_thin_wall_applicability
name: Verify Thin-Wall Applicability

goal_class: validation_goal

target_parameter: PARAM-thin-wall-applicability

required_facts:
  - parameter: PARAM-required-wall-thickness
  - parameter: PARAM-outside-diameter

satisfaction:
  status: pending
  satisfied_by: null
  required_output:
    parameter: PARAM-thin-wall-applicability

authority:
  references:
    - B313-304.1.2

provenance:
  execution_context_id: EXEC-2026-000001
  task_id: TASK-pipe-wall-thickness-001
  workflow_id: WF-pipe-wall-thickness-design
  created_by: planner
  timestamp: 2026-07-02T10:33:00Z

state:
  status: blocked
  blocked_by:
    - PARAM-required-wall-thickness
    - PARAM-outside-diameter
  parent_goal: GOAL-required-wall-thickness-001
  child_goals: []

metadata:
  version: 1
---
```

---

# Allowed relationships

Goals may connect to:

```yaml
requires_fact
satisfied_by
expands_to
parent_goal
child_goal
blocked_by
created_from_workflow
governed_by
executed_by
produced_fact
failed_because
superseded_by
```

Example:

```yaml
edges:
  - type: requires_fact
    target: PARAM-design-pressure

  - type: satisfied_by
    target: FACT-required-wall-thickness-001

  - type: governed_by
    target: B313-304.1.2

  - type: created_from_workflow
    target: WF-pipe-wall-thickness-design
```

---

# Planner/Kernal boundary

The Planner may:

```text
create Goals
expand Goals
identify missing Facts
rank possible paths
ask user for missing input
```

The Kernel may:

```text
execute ready Goals
mark Goals as blocked
mark Goals as satisfied
record produced Facts
record execution state
```

The Goal itself does not perform execution.

---

# Forbidden fields

Goal nodes must not contain:

```yaml
formula:
calculation_result:
numeric_result:
unit_conversion_rule:
standard_text:
parameter_definition:
concept_definition:
```

Those belong to Equations, Facts, Units, Paragraphs, Parameters, or Concepts.

---

# Validation rules

A Goal is invalid if:

1. `type` is not `goal`.
    
2. `goal_class` is missing.
    
3. It has no target Parameter, except pure report/explanation Goals.
    
4. It claims to be satisfied without a valid Fact or accepted terminal state.
    
5. It stores a calculated value directly.
    
6. It modifies immutable knowledge.
    
7. It has cyclic parent/child Goal relationships.
    
8. It lacks provenance.
    
9. It bypasses Authority Context when authority is required.
    
10. It is marked complete while required child Goals remain unresolved.
    

---

# Conceptual rule

```text
Goal defines what is desired.
Parameter defines what kind of result is desired.
Fact proves that the Goal has been satisfied.
Planner expands Goals.
Kernel executes ready Goals.
```