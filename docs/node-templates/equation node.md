# Equation Node Template

> **Implementation:** B31.3 equation sources at [`knowledge/standards/asme/asme_b31.3/nodes/equation/`](../../knowledge/standards/asme/asme_b31.3/nodes/equation/) use ids prefixed with `asme_b313_*` (e.g. `asme_b313_304_1_2_wall_thickness`) to avoid cross-standard numbering collisions. Validator: [`engine/validation/equation_node_validator.py`](../../engine/validation/equation_node_validator.py). Legacy executor fields (`variables`, `steps`, `executor`) live in sidecars under `equation/{id}/execution.yaml`, merged at load time by [`engine/reference/equation_sidecar.py`](../../engine/reference/equation_sidecar.py) and [`engine/graph/graph_builder.py`](../../engine/graph/graph_builder.py). Paragraph/workflow execution sidecars keep slim `equations: [{id, file}]` references. Runtime `B313-eq-*` ids are aliases only — see [`engine/reference/b313_legacy_aliases.py`](../../engine/reference/b313_legacy_aliases.py). On-disk graph edges use taxonomy types (`authorized_by`, `requires_parameter`, `calculates_parameter`, …) with `param-*` targets from nomenclature. See [`Paragraph Node.md`](Paragraph%20Node.md) and [`_relationship_schema.md`](_relationship_schema.md).

An Equation node defines a deterministic **calculation** that produces engineering quantities.

An Equation consumes input Parameters through runtime Facts.  
An Equation produces output Parameters through derived Facts.

A Paragraph may authorize or reference an Equation.  
The Equation defines the executable mathematical or formula relationship only.

For table resolution use [`lookup.md`](lookup.md).  
For pass/fail checks use [`validation_rule.md`](validation_rule.md).

Do **not** author a top-level `links` metadata block — object relationships belong in typed `edges` only ([`_relationship_schema.md`](_relationship_schema.md#on-disk-rule)). **Exception:** declare governing paragraphs in `authority.authorized_by` (not in `edges`); the graph compiler emits `authorized_by` edges at build time.

```yaml
---
id: EQ-asme-B313-304-1-2
type: equation

key: asme_b313_304_1_1
name: Internal Pressure Wall Thickness Equation

equation_class: calculation
calculation_kind: algebraic

description: >
  Calculates pressure design wall thickness for straight pipe under internal
  pressure using the ASME B31.3 internal pressure equation.

authority:
  authorized_by:
    - 304.1.2-a
  authority_context_required: true

display:
  latex: "t = \\frac{P D}{2(SEW + P Y)}"
  text: "t = PD / 2(SEW + PY)"

expression:
  language: sympy
  formula: "t = P * D / (2 * (S * E * W + P * Y))"

requires:
  - parameter: PARAM-design-pressure
    symbol: P
    required: true
    dimension: DIM-pressure

  - parameter: PARAM-outside-diameter
    symbol: D
    required: true
    dimension: DIM-length

  - parameter: PARAM-allowable-stress
    symbol: S
    required: true
    dimension: DIM-pressure

  - parameter: PARAM-weld-joint-efficiency
    symbol: E
    required: true
    dimension: DIM-dimensionless

  - parameter: PARAM-weld-strength-reduction-factor-W
    symbol: W
    required: true
    dimension: DIM-dimensionless

  - parameter: PARAM-temperature-coefficient-Y
    symbol: Y
    required: true
    dimension: DIM-dimensionless

calculates:
  - parameter: PARAM-required-wall-thickness
    symbol: t
    dimension: DIM-length

applicability:
  applies_when:
    - parameter: PARAM-pressure-loading
      operator: equals
      value: internal_pressure

    - parameter: PARAM-straight-pipe-section
      operator: equals
      value: true

validation:
  dimensional_check: true
  requires_authority_context: true
  warnings: []

edges:
  - type: requires_parameter
    target: PARAM-design-pressure

  - type: requires_parameter
    target: PARAM-outside-diameter

  - type: calculates_parameter
    target: PARAM-required-wall-thickness

metadata:
  status: active
  version: 1
---
```

---

# Purpose

An Equation answers:

```text
How is one engineering quantity calculated from other Facts?
```

Examples:

```text
t = PD / 2(SEW + PY)
t_m = t + c
P_test = 1.5 × P_design
MAWP = function(thickness, stress, diameter)
```

Do not use Equation nodes for table lookups or validation checks.

An Equation does not store runtime values.  
It defines the relationship used to produce runtime Facts.

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Stable equation identity. Must use `EQ-*` or project convention.|
|`type`|Must be `equation`.|
|`key`|Machine-safe equation key.|
|`name`|Human-readable equation name.|
|`equation_class`|Kind of equation.|
|`description`|Stable engineering description.|
|`requires`|Input Parameters required by the equation.|
|`calculates`|Output Parameters produced by the equation.|
|`metadata`|Status and versioning.|

---

# Recommended `equation_class` values

```yaml
calculation
aggregation
transformation
```

Equations produce calculated engineering quantities only.  
Do not use `lookup`, `validation`, `condition`, `selection`, or `comparison` — use dedicated node types.

---

# Recommended `calculation_kind` values

```yaml
algebraic
piecewise
conditional
iterative
function
```

---

# Equation vs Paragraph

A Paragraph provides authority.

An Equation provides deterministic structure.

```text
Paragraph:
  ASME B31.3 §304.1.2 authorizes the wall-thickness relationship.

Equation:
  Defines the machine-readable formula and required Parameters.
```

Correct:

```yaml
authority:
  authorized_by:
    - 304.1.2-a
  authority_context_required: true
```

Do not duplicate `authorized_by` on `edges`.

Incorrect:

```text
The Paragraph itself directly stores runtime calculation results.
```

---

# Equation vs Fact

An Equation defines the relationship.

A Fact records the result.

```text
EQ-B313-wall-thickness
  consumes:
    Fact: design_pressure = 8 bar
    Fact: outside_diameter = 168.3 mm
    Fact: allowable_stress = 138 MPa

  produces:
    Fact: required_wall_thickness = 4.82 mm
```

---

# Requires model

The `requires` section defines input Parameters.

```yaml
requires:
  - parameter: PARAM-design-pressure
    symbol: P
    required: true
    dimension: DIM-pressure
```

This does not mean the Equation stores the value of `P`.

It means that during execution, the Kernel must find an active Fact that instantiates `PARAM-design-pressure`.

---

# Calculates model

The `calculates` section defines output Parameters.

```yaml
calculates:
  - parameter: PARAM-required-wall-thickness
    symbol: t
    dimension: DIM-length
```

During execution, the result becomes a derived Fact:

```text
FACT-required-wall-thickness-001
```

---

# Display model

Equations should have both human and machine forms.

```yaml
display:
  latex: "t = \\frac{P D}{2(SEW + PY)}"
  text: "t = PD / 2(SEW + PY)"
```

The report uses the display form.

The execution engine uses the expression or function form.

---

# Expression model

For simple algebraic equations:

```yaml
expression:
  language: sympy
  formula: "t = P * D / (2 * (S * E * W + P * Y))"
```

For safe Python-backed deterministic functions:

```yaml
executor:
  function: calculate_wall_thickness
  module: engine.executor.functions
```

---

# Example: minimum required thickness

```yaml
---
id: EQ-B313-minimum-required-thickness
type: equation

key: b313_minimum_required_thickness
name: Minimum Required Thickness Equation

equation_class: calculation
calculation_kind: algebraic

description: >
  Calculates minimum required pipe wall thickness including corrosion or
  mechanical allowance.

authority:
  authorized_by:
    - 304.1.1-a
  authority_context_required: true

display:
  latex: "t_m = t + c"
  text: "t_m = t + c"

expression:
  language: sympy
  formula: "t_m = t + c"

requires:
  - parameter: PARAM-required-wall-thickness
    symbol: t
    required: true
    dimension: DIM-length

  - parameter: PARAM-corrosion-allowance
    symbol: c
    required: true
    dimension: DIM-length

calculates:
  - parameter: PARAM-minimum-required-thickness
    symbol: t_m
    dimension: DIM-length

edges:
  - type: requires_parameter
    target: PARAM-required-wall-thickness

  - type: requires_parameter
    target: PARAM-corrosion-allowance

  - type: calculates_parameter
    target: PARAM-minimum-required-thickness

metadata:
  status: active
  version: 1
---
```

---

# Applicability model

Equations may have applicability rules.

```yaml
applicability:
  applies_when:
    - parameter: PARAM-pressure-loading
      operator: equals
      value: internal_pressure
```

Applicability determines whether this Equation is available in a given execution.

Applicability does not execute the Equation.

---

# Validation model

```yaml
validation:
  dimensional_check: true
  requires_authority_context: true
  warnings: []
```

The system should verify:

```text
Input Facts match required dimensions.
Output dimension matches the calculated expression.
Authority Context activates the authorizing Paragraph.
Required Facts exist before execution.
```

---

# Allowed relationships

Equation nodes may use these edge types on `edges`:

```yaml
requires_parameter
calculates_parameter
depends_on_equation
references_concept
supersedes
superseded_by
```

Governing paragraphs belong in `authority.authorized_by` (see [Equation vs Paragraph](#equation-vs-paragraph)) — not as `authorized_by` edges.

Example:

```yaml
authority:
  authorized_by:
    - 304.1.2-a
  authority_context_required: true

edges:
  - type: requires_parameter
    target: PARAM-design-pressure

  - type: calculates_parameter
    target: PARAM-required-wall-thickness
```

---

# Forbidden fields

Equation nodes must not contain runtime execution values.

Forbidden:

```yaml
runtime_value:
fact_value:
user_input:
execution_id:
task_id:
calculation_result:
selected_for_execution:
active_in_context:
```

Equation nodes should also not contain full Paragraph text. They should reference the Paragraph that authorizes them.

---

# Unit transformation equations

Global unit conversions use `equation_class: transformation` with ids prefixed `EQ-unit-*`. They live in the units pack (`knowledge/global/units/nodes/equation/`) and are linked from unit `converts_to` edges.

No `authority` block is required. Use `symbol` + `unit` in `requires` / `calculates` instead of `PARAM-*` nodes.

```yaml
---
id: EQ-unit-degC-to-degF
type: equation

key: unit_degC_to_degF
name: Celsius to Fahrenheit

equation_class: transformation
calculation_kind: algebraic

description: >
  Convert temperature from degrees Celsius to degrees Fahrenheit.

conversion:
  from_unit: UNIT-degC
  to_unit: UNIT-degF

display:
  text: "F = C * 9/5 + 32"
  latex: "F = \\frac{9}{5}C + 32"

expression:
  language: sympy
  formula: "F = C * 9 / 5 + 32"

requires:
  - symbol: C
    unit: UNIT-degC

calculates:
  - symbol: F
    unit: UNIT-degF

metadata:
  status: active
  version: 1
---
```

Unit nodes reference these via:

```yaml
- type: converts_to
  target: UNIT-degF
  equation: EQ-unit-degC-to-degF
```

Each directed conversion pair needs its own equation and edge. Do not rely on automatic inversion.

---

# Validation rules

An Equation node is invalid if:

1. `type` is not `equation`.
2. `equation_class` is not `calculation`, `aggregation`, or `transformation`.
3. It has no `requires` list unless it is a constant authority-defined value.
4. It has no `calculates` list.
5. It stores runtime values.
6. It references unknown Parameters.
7. It calculates a Parameter whose dimension conflicts with the expression result.
8. It has no authorizing Paragraph when derived from a standard (not required for `EQ-unit-*` transformation equations).
9. It duplicates Paragraph text instead of referencing the Paragraph.
10. It models lookup or validation behavior (use `lookup` or `validation_rule` types).
    

---

# Conceptual rule

```text
Paragraph authorizes the Equation.
Equation defines the deterministic relationship.
Parameter defines the meaning of inputs and outputs.
Fact supplies input values and records output values.
Execution Context records the run.
Report explains the chain.
```