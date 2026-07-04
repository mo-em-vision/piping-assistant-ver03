# Fact Node

> **Implementation:** [`models/fact.py`](../../models/fact.py) and [`models/fact_store.py`](../../models/fact_store.py) on `Task.execution_context.fact_store`. Not a knowledge-graph node type.

A Fact represents a runtime engineering value, assertion, selection, or result about a Parameter.

A Fact is not part of the immutable knowledge graph.  
A Fact belongs to an Execution Context, Project, Task, or Report trace.

```yaml
---
id: FACT-2026-000001
type: fact

parameter: PARAM-design-pressure
key: design_pressure

value:
  amount: 8
  unit: UNIT-bar

canonical_value:
  amount: 800000
  unit: UNIT-Pa

fact_class: user_supplied

source:
  source_type: user_input
  source_id: USER
  description: >
    Provided by user during pipe wall thickness design input collection.

provenance:
  execution_context_id: EXEC-2026-000001
  task_id: TASK-pipe-wall-thickness-001
  workflow_id: WF-pipe-wall-thickness-design
  collected_at_node: 304.1.2-a
  collected_at_phase: parameter_gathering
  timestamp: 2026-07-02T10:30:00Z

validation:
  status: confirmed
  unit_validated: true
  dimension: DIM-pressure
  warnings: []

supersession:
  supersedes: null
  superseded_by: null
  active: true

metadata:
  version: 1
---
```

---

# Purpose

Facts instantiate Parameters during execution.

Example:

```text
Parameter:
  PARAM-design-pressure

Fact:
  Design Pressure = 8 bar
```

The Parameter defines the engineering meaning.  
The Fact stores the actual runtime value.

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Runtime Fact identity.|
|`type`|Must be `fact`.|
|`parameter`|The `PARAM-*` node this Fact instantiates.|
|`key`|Runtime field key, usually inherited from the Parameter.|
|`fact_class`|How the Fact was created.|
|`source`|Origin of the Fact.|
|`provenance`|Execution trace and context.|
|`validation`|Validation status.|
|`supersession`|Append-only correction tracking.|

---

# Value rules

A Fact may store different kinds of values depending on the Parameter class.

## Numeric value

```yaml
value:
  amount: 8
  unit: UNIT-bar

canonical_value:
  amount: 800000
  unit: UNIT-Pa
```

Used for:

```text
pressure
temperature
length
density
stress
velocity
```

---

## Categorical value

```yaml
value:
  label: ASTM A106 Grade B
  normalized_key: astm_a106_grade_b
```

Used for:

```text
material specification
joint category
pipe schedule
fluid service category
```

---

## Boolean value

```yaml
value:
  boolean: true
```

Used for:

```text
straight pipe section
internal pressure loading confirmed
default accepted
```

---

## Structured value

```yaml
value:
  object:
    material_standard: ASTM A106
    grade: B
    product_form: seamless pipe
```

Used only when the value cannot be represented safely as a scalar.

---

# `fact_class`

Recommended values:

```yaml
user_supplied
calculated
looked_up
imported
default_confirmed
assumed
validated
derived
system_generated
```

---

# Source model

The `source` field records where the Fact came from.

## User supplied

```yaml
source:
  source_type: user_input
  source_id: USER
  description: Provided by user.
```

## Table lookup

```yaml
source:
  source_type: table_lookup
  source_id: TABLE-B313-A1
  lookup_node: LOOKUP-B313-material-allowable-stress
  description: >
    Retrieved from ASME B31.3 allowable stress table.
```

## Equation result

```yaml
source:
  source_type: equation
  source_id: EQ-B313-wall-thickness
  input_facts:
    - FACT-design-pressure-001
    - FACT-outside-diameter-001
    - FACT-allowable-stress-001
```

## Validation rule result

```yaml
source:
  source_type: validation_rule
  source_id: VALRULE-B313-thin-wall-check
  input_facts:
    - FACT-required-wall-thickness-001
    - FACT-outside-diameter-001
```

## Default confirmed by user

```yaml
source:
  source_type: default_confirmed
  source_id: 304.1.2-a
  description: >
    Default coefficient accepted by user.
```

---

# Provenance model

Every Fact must be traceable.

```yaml
provenance:
  execution_context_id: EXEC-2026-000001
  task_id: TASK-pipe-wall-thickness-001
  workflow_id: WF-pipe-wall-thickness-design
  goal_id: GOAL-required-wall-thickness
  created_by: kernel
  timestamp: 2026-07-02T10:30:00Z
```

Recommended provenance fields:

|Field|Purpose|
|---|---|
|`execution_context_id`|Runtime execution context.|
|`task_id`|User task.|
|`project_id`|Persistent project, if applicable.|
|`workflow_id`|Workflow that required or produced the Fact.|
|`goal_id`|Goal this Fact helps satisfy.|
|`created_by`|User, planner, kernel, lookup, import, etc.|
|`timestamp`|Creation time.|

---

# Validation model

```yaml
validation:
  status: confirmed
  unit_validated: true
  dimension: DIM-pressure
  warnings: []
  errors: []
```

Recommended statuses:

```yaml
pending
confirmed
validated
rejected
superseded
conflicting
```

---

# Append-only correction model

Facts are append-only.

Do not edit an existing Fact when the value changes.

Instead, create a new Fact and supersede the previous one.

Example:

```yaml
supersession:
  supersedes: FACT-design-temperature-001
  superseded_by: null
  active: true
  reason: User corrected design temperature.
```

The old Fact becomes:

```yaml
supersession:
  supersedes: null
  superseded_by: FACT-design-temperature-002
  active: false
```

---

# Example: material specification Fact

```yaml
---
id: FACT-material-specification-001
type: fact

parameter: PARAM-material-specification
key: material_specification

value:
  label: ASTM A106 Grade B
  normalized_key: astm_a106_grade_b

fact_class: user_supplied

source:
  source_type: user_input
  source_id: USER
  description: >
    Material specification provided by user.

provenance:
  execution_context_id: EXEC-2026-000001
  task_id: TASK-pipe-wall-thickness-001
  workflow_id: WF-pipe-wall-thickness-design
  collected_at_node: B313-304.1.1
  collected_at_phase: parameter_gathering
  timestamp: 2026-07-02T10:30:00Z

validation:
  status: confirmed
  warnings: []

supersession:
  supersedes: null
  superseded_by: null
  active: true

metadata:
  version: 1
---
```

---

# Example: allowable stress lookup Fact

```yaml
---
id: FACT-allowable-stress-001
type: fact

parameter: PARAM-allowable-stress
key: allowable_stress

value:
  amount: 20000
  unit: UNIT-psi

canonical_value:
  amount: 137895145.86336
  unit: UNIT-Pa

fact_class: looked_up

source:
  source_type: table_lookup
  source_id: TABLE-B313-material-allowable-stress
  lookup_node: LOOKUP-B313-material-allowable-stress
  input_facts:
    - FACT-material-specification-001
    - FACT-design-temperature-001

provenance:
  execution_context_id: EXEC-2026-000001
  task_id: TASK-pipe-wall-thickness-001
  workflow_id: WF-pipe-wall-thickness-design
  produced_by_node: B313-material-stress
  timestamp: 2026-07-02T10:31:00Z

validation:
  status: validated
  unit_validated: true
  dimension: DIM-pressure
  warnings: []

supersession:
  supersedes: null
  superseded_by: null
  active: true

metadata:
  version: 1
---
```

---

# Example: calculated wall thickness Fact

```yaml
---
id: FACT-required-wall-thickness-001
type: fact

parameter: PARAM-required-wall-thickness
key: required_wall_thickness

value:
  amount: 4.82
  unit: UNIT-mm

canonical_value:
  amount: 0.00482
  unit: UNIT-m

fact_class: calculated

source:
  source_type: equation
  source_id: EQ-B313-wall-thickness
  input_facts:
    - FACT-design-pressure-001
    - FACT-outside-diameter-001
    - FACT-allowable-stress-001
    - FACT-joint-efficiency-001
    - FACT-weld-strength-reduction-factor-001
    - FACT-temperature-coefficient-Y-001

provenance:
  execution_context_id: EXEC-2026-000001
  task_id: TASK-pipe-wall-thickness-001
  workflow_id: WF-pipe-wall-thickness-design
  goal_id: GOAL-required-wall-thickness
  produced_by_node: 304.1.2-a
  timestamp: 2026-07-02T10:32:00Z

validation:
  status: validated
  unit_validated: true
  dimension: DIM-length
  warnings: []

supersession:
  supersedes: null
  superseded_by: null
  active: true

metadata:
  version: 1
---
```

---

# Allowed relationships

Facts may connect to:

```yaml
instantiates
derived_from
looked_up_from
validated_by
satisfies_goal
produced_by
supersedes
conflicts_with
belongs_to_execution_context
belongs_to_project
included_in_report
```

Example:

```yaml
edges:
  - type: instantiates
    target: PARAM-design-pressure

  - type: satisfies_goal
    target: GOAL-required-wall-thickness

  - type: produced_by
    target: EQ-B313-wall-thickness
```

---

# Forbidden fields

Facts must not define engineering meaning.

Facts must not contain:

```yaml
concept_definition:
dimension_definition:
unit_conversion_rule:
parameter_aliases:
equation_formula:
standard_text:
workflow_definition:
```

Those belong to immutable knowledge nodes.

---

# Validation rules

A Fact is invalid if:

1. `type` is not `fact`.
    
2. `parameter` does not reference a valid `PARAM-*` node.
    
3. The value type is incompatible with the Parameter class.
    
4. A numeric Fact uses a unit not allowed by the Parameter dimension.
    
5. A numeric Fact has no canonical converted value.
    
6. A derived Fact does not record input Facts.
    
7. A looked-up Fact does not record lookup/table provenance.
    
8. A user-supplied Fact does not record user/input provenance.
    
9. A correction modifies an old Fact instead of superseding it.
    
10. A Fact redefines Parameter meaning.
    

---

# Conceptual rule

```text
Parameter defines what the value means.
Fact records what value is known.
Provenance explains where the value came from.
Supersession preserves history.
```