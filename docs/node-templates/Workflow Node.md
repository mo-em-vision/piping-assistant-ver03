# Workflow Node Template

> **Implementation:** B31.3 workflow sources at [`knowledge/standards/asme/asme_b31.3/nodes/workflows/`](../../knowledge/standards/asme/asme_b31.3/nodes/workflows/) use ids `WF-PIPE-WALL-THICKNESS` and `WF-MAWP` with machine keys `pipe_wall_thickness_design` and `mawp_design`. Validator: [`engine/validation/workflow_node_validator.py`](../../engine/validation/workflow_node_validator.py). Legacy runtime fields (`navigation`, `assumptions`, `interactions`, `inputs`, `equations`, `nomenclature`, …) live in sidecars under `workflows/{id}/runtime.yaml`, merged at load time by [`engine/reference/workflow_sidecar.py`](../../engine/reference/workflow_sidecar.py) and [`engine/graph/graph_builder.py`](../../engine/graph/graph_builder.py). Template `phases` synthesize `navigation` when no sidecar is present. On-disk graph edges use native taxonomy types (`starts_from_paragraph`, `may_use_equation`, `requires_parameter`, …); legacy `references` + `role` is accepted only at migration/import. Runtime routing keeps `next` edges with `when` conditions. Slug aliases `B313-WF-*` remain in [`engine/reference/b313_legacy_aliases.py`](../../engine/reference/b313_legacy_aliases.py).

A Workflow node defines a reusable engineering objective and the structured path for satisfying it.

A Workflow does not store runtime values.  
A Workflow does not execute calculations.  
A Workflow does not replace the Planner, Graph Engine, or Execution Kernel.

Instead, a Workflow defines:

```text
What kind of engineering task this is.
Which Goals may be created.
Which authority sources may be required.
Which Parameters are expected.
Which Equations, Paragraphs, and validation checks may participate.
```

```yaml
---
id: WF-pipe-wall-thickness-design
type: workflow

key: pipe_wall_thickness_design
name: Pipe Wall Thickness Design

workflow_class: design_calculation

description: >
  Determines required pipe wall thickness for pressure design using the
  applicable governing authority, material properties, pipe geometry,
  design conditions, and allowance requirements.

domain:
  - piping

primary_goal_template: GOALTEMPLATE-required-wall-thickness

expected_authorities:
  - AUTH-ASME-B31.3
  - AUTH-ASME-B36.10M
  - AUTH-ASTM-A106
  - AUTH-ASTM-A312

entry_points:
  - paragraph: B313-304.1.1
    role: definition_anchor

  - paragraph: B313-304.1.2
    role: internal_pressure_branch

  - paragraph: B313-304.1.3
    role: external_pressure_branch

expected_parameters:
  - PARAM-straight-pipe-section
  - PARAM-pressure-loading
  - PARAM-design-pressure
  - PARAM-outside-diameter
  - PARAM-material-specification
  - PARAM-design-temperature
  - PARAM-allowable-stress
  - PARAM-weld-joint-efficiency
  - PARAM-weld-strength-reduction-factor-W
  - PARAM-temperature-coefficient-Y
  - PARAM-corrosion-allowance
  - PARAM-required-wall-thickness
  - PARAM-minimum-required-thickness

goal_expansion:
  root_goal:
    goal_class: calculation_goal
    target_parameter: PARAM-minimum-required-thickness

  child_goal_templates:
    - goal_class: input_goal
      target_parameter: PARAM-straight-pipe-section

    - goal_class: selection_goal
      target_parameter: PARAM-pressure-loading

    - goal_class: lookup_goal
      target_parameter: PARAM-allowable-stress

    - goal_class: calculation_goal
      target_parameter: PARAM-required-wall-thickness

    - goal_class: validation_goal
      target_parameter: PARAM-thin-wall-applicability

    - goal_class: calculation_goal
      target_parameter: PARAM-minimum-required-thickness

phases:
  - key: expansion_assumptions
    purpose: Confirm assumptions required before graph expansion.
    required_parameters:
      - PARAM-straight-pipe-section

  - key: path_decisions
    purpose: Select applicable pressure loading branch.
    required_parameters:
      - PARAM-pressure-loading

  - key: parameter_gathering
    purpose: Collect design conditions and geometry.
    required_parameters:
      - PARAM-design-pressure
      - PARAM-outside-diameter
      - PARAM-material-specification
      - PARAM-design-temperature

  - key: coefficient_resolution
    purpose: Resolve coefficients required by the pressure design equation.
    required_parameters:
      - PARAM-weld-joint-efficiency
      - PARAM-weld-strength-reduction-factor-W
      - PARAM-temperature-coefficient-Y

  - key: execution_assumptions
    purpose: Resolve allowances and post-calculation assumptions.
    required_parameters:
      - PARAM-corrosion-allowance

applicability:
  applies_to:
    - CONCEPT-pipe
    - CONCEPT-wall-thickness
    - CONCEPT-pressure

edges:
  - type: uses_authority
    target: AUTH-ASME-B31.3

  - type: starts_from_paragraph
    target: B313-304.1.1

  - type: may_use_equation
    target: EQ-B313-wall-thickness

  - type: may_create_goal
    target: GOALTEMPLATE-required-wall-thickness

  - type: requires_parameter
    target: PARAM-design-pressure

metadata:
  status: active
  version: 1
---
```

---

# Purpose

A Workflow answers:

```text
What kind of engineering work is the system trying to perform?
```

Examples:

```text
Pipe Wall Thickness Design
Pipe Integrity Verification
Pressure Test Verification
Allowable Stress Resolution
Material Property Lookup
API 570 Inspection Planning
Tank Shell Thickness Calculation
Pressure Vessel MAWP Calculation
```

A Workflow is reusable knowledge.

A Workflow instance inside an execution becomes runtime state, but the Workflow node itself remains immutable.

---

# Workflow vs Goal

```text
Workflow = reusable engineering task pattern.
Goal = runtime objective created during execution.
```

Example:

```text
WF-pipe-wall-thickness-design
  creates
GOAL-required-wall-thickness-001
```

The Workflow defines the pattern.  
The Goal tracks the actual runtime objective.

---

# Workflow vs Procedure

A Workflow is not a rigid step-by-step script.

It should not say:

```text
Step 1: Ask pressure.
Step 2: Ask material.
Step 3: Calculate.
```

Instead, it should define:

```text
Expected goals
Required parameter groups
Applicable authority
Possible branches
Required validation
Report expectations
```

The Planner and Graph Engine determine the actual path based on missing Facts, authority context, and applicability.

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Stable workflow identity. Must use `WF-*`.|
|`type`|Must be `workflow`.|
|`key`|Machine-safe workflow key.|
|`name`|Human-readable workflow name.|
|`workflow_class`|Kind of workflow.|
|`description`|Stable engineering description.|
|`metadata`|Status and versioning.|

---

# Recommended `workflow_class` values

```yaml
design_calculation
verification
inspection
assessment
lookup
selection
reporting
screening
troubleshooting
```

---

# Expected authorities

Workflows may list expected authorities.

```yaml
expected_authorities:
  - AUTH-ASME-B31.3
  - AUTH-ASME-B36.10M
```

This does not automatically activate those authorities.

The Authority Context decides which authorities are active during a specific execution.

---

# Entry points

Entry points identify likely graph anchors.

```yaml
entry_points:
  - paragraph: B313-304.1.1
    role: definition_anchor

  - paragraph: B313-304.1.2
    role: internal_pressure_branch
```

The Planner may use these entry points, but the Graph Engine still resolves dependencies and applicability.

---

# Expected parameters

Expected Parameters define what this Workflow may need.

```yaml
expected_parameters:
  - PARAM-design-pressure
  - PARAM-material-specification
  - PARAM-required-wall-thickness
```

This does not mean all Parameters are requested immediately.

The Planner should request only what is needed for the current phase or blocked Goal.

---

# Goal expansion

A Workflow may define a goal expansion pattern.

```yaml
goal_expansion:
  root_goal:
    goal_class: calculation_goal
    target_parameter: PARAM-minimum-required-thickness

  child_goal_templates:
    - goal_class: lookup_goal
      target_parameter: PARAM-allowable-stress
```

These are templates for runtime Goals.

They are not runtime Goals themselves.

---

# Phases

Phases define a disciplined interaction sequence.

```yaml
phases:
  - key: expansion_assumptions
    required_parameters:
      - PARAM-straight-pipe-section
```

Phases are useful for avoiding premature input collection.

For example:

```text
Do not request design pressure until the system knows the user is analyzing a supported pipe geometry.
```

---

# Branching model

Workflows may define possible branches.

```yaml
branches:
  - key: internal_pressure
    selected_when:
      parameter: PARAM-pressure-loading
      value: internal_pressure
    entry_point: B313-304.1.2

  - key: external_pressure
    selected_when:
      parameter: PARAM-pressure-loading
      value: external_pressure
    entry_point: B313-304.1.3
```

Branching does not execute.  
It informs Planner/Graph expansion.

---

# Example: material property lookup workflow

```yaml
---
id: WF-material-property-lookup
type: workflow

key: material_property_lookup
name: Material Property Lookup

workflow_class: lookup

description: >
  Resolves material properties from active material standards or design codes.

expected_authorities:
  - AUTH-ASTM-A106
  - AUTH-ASTM-A312
  - AUTH-ASME-B31.3

expected_parameters:
  - PARAM-material-specification
  - PARAM-material-grade
  - PARAM-design-temperature
  - PARAM-material-density
  - PARAM-yield-strength
  - PARAM-tensile-strength
  - PARAM-allowable-stress

goal_expansion:
  root_goal:
    goal_class: lookup_goal
    target_parameter: PARAM-material-property

phases:
  - key: material_identification
    required_parameters:
      - PARAM-material-specification

  - key: property_selection
    required_parameters:
      - PARAM-requested-material-property

  - key: authority_resolution
    required_parameters:
      - PARAM-design-temperature

edges:
  - type: may_use_authority
    target: AUTH-ASTM-A106

  - type: may_use_authority
    target: AUTH-ASME-B31.3

metadata:
  status: active
  version: 1
---
```

---

# Example: pipe integrity verification workflow

```yaml
---
id: WF-pipe-integrity-verification
type: workflow

key: pipe_integrity_verification
name: Pipe Integrity Verification

workflow_class: verification

description: >
  Verifies whether a piping component satisfies selected integrity,
  pressure design, inspection, and acceptance criteria under the active
  authority context.

expected_authorities:
  - AUTH-ASME-B31.3
  - AUTH-API-570
  - AUTH-COMPANY-PIPING-SPEC

expected_parameters:
  - PARAM-material-specification
  - PARAM-design-pressure
  - PARAM-design-temperature
  - PARAM-measured-wall-thickness
  - PARAM-required-wall-thickness
  - PARAM-corrosion-allowance
  - PARAM-corrosion-rate
  - PARAM-remaining-life
  - PARAM-code-compliance-status

goal_expansion:
  root_goal:
    goal_class: verification_goal
    target_parameter: PARAM-code-compliance-status

  child_goal_templates:
    - goal_class: calculation_goal
      target_parameter: PARAM-required-wall-thickness

    - goal_class: comparison
      target_parameter: PARAM-thickness-acceptability

    - goal_class: calculation_goal
      target_parameter: PARAM-remaining-life

metadata:
  status: draft
  version: 1
---
```

---

# Allowed relationships

Workflow nodes may use:

```yaml
uses_authority
may_use_authority
starts_from_paragraph
requires_parameter
produces_parameter
may_create_goal
may_use_equation
requires_validation
has_phase
has_branch
supersedes
superseded_by
```

Example:

```yaml
edges:
  - type: starts_from_paragraph
    target: B313-304.1.1

  - type: may_use_equation
    target: EQ-B313-wall-thickness

  - type: requires_parameter
    target: PARAM-design-pressure
```

---

# Report expectations

Workflows may define report requirements.

```yaml
report:
  report_type: calculation_report
  required_sections:
    - objective
    - authority_context
    - inputs
    - equations
    - calculations
    - validation
    - warnings
    - conclusion
```

This defines what the report should include, not the report content itself.

---

# Forbidden fields

Workflow nodes must not contain runtime execution values.

Forbidden:

```yaml
fact_value:
user_input:
runtime_result:
execution_id:
task_id:
current_phase:
active_goal_id:
calculation_result:
```

Runtime state belongs to Goals and Execution Context.

---

# Validation rules

A Workflow node is invalid if:

1. `type` is not `workflow`.
    
2. `id` does not start with `WF-`.
    
3. `key` is missing or not unique.
    
4. It stores runtime values.
    
5. It hard-codes execution results.
    
6. It bypasses Authority Context for standards-governed workflows.
    
7. It defines Paragraph text instead of referencing Paragraphs.
    
8. It defines Equation formulas instead of referencing Equations.
    
9. It requests all possible inputs at once instead of supporting phased or goal-driven collection.
    
10. It acts as a rigid script where dependency-driven execution is required.
    

---

# Conceptual rule

```text
Workflow defines the engineering task pattern.
Goal defines the runtime objective.
Parameter defines what information may be needed.
Fact records what information is known.
Authority Context determines what governs.
Graph and Planner determine the actual path.
Execution produces the result.
```