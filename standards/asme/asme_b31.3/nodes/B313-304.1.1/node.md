---
# ==========================================
# Node Identity
# ==========================================

id: B313-304.1.1
type: calculation
title: Required Thickness Under Internal Pressure
version: "1.0"
status: draft
created: "2026-06-17"
modified: "2026-06-17"

# ==========================================
# Standard Context
# ==========================================

paragraph: "304.1.1"
section: "304 Pressure Design of Piping Components"
topic: wall_thickness

# ==========================================
# Purpose
# ==========================================

purpose: Calculate the minimum required wall thickness for straight pipe under internal pressure using the thin-wall pressure design equation.
engineering_intent: pipe_wall_thickness_design

# ==========================================
# Dependencies
# ==========================================

depends_on:
  - node_id: B313-material-stress
    dependency_type: calculation

# ==========================================
# Inputs
# ==========================================

inputs:
  - id: design_pressure
    name: P
    description: Internal design pressure
    required: true
    source: user_input
    unit: Pa
    allowed_units: [Pa, bar, psi]
    validation: positive
    requires_confirmation: false

  - id: outside_diameter
    name: D
    description: Outside diameter of pipe
    required: true
    source: user_input
    unit: mm
    allowed_units: [mm, in]
    validation: positive
    requires_confirmation: false

  - id: allowable_stress
    name: S
    description: Allowable stress at design temperature
    required: true
    source: node_output
    unit: Pa
    allowed_units: [Pa, psi]
    validation: positive
    requires_confirmation: false

  - id: weld_joint_efficiency
    name: E
    description: Weld joint quality factor
    required: true
    source: default
    unit: dimensionless
    default: 1.0
    requires_confirmation: true

  - id: weld_strength_reduction
    name: W
    description: Weld strength reduction factor
    required: true
    source: default
    unit: dimensionless
    default: 1.0
    requires_confirmation: true

  - id: temperature_coefficient
    name: Y
    description: Temperature coefficient for material
    required: true
    source: default
    unit: dimensionless
    default: 0.4
    requires_confirmation: true

# ==========================================
# Outputs
# ==========================================

outputs:
  - id: required_thickness
    name: t
    description: Minimum required wall thickness from pressure design
    unit: mm
    type: quantity
    used_by: []

# ==========================================
# Conditions
# ==========================================

conditions:
  - id: thin_wall_check
    name: thin_wall_check
    expression: "t < D/6"
    description: Verify thin-wall pressure design equation applicability
    result_if_true: Continue with thin-wall calculation per formulas/wall_thickness.md
    result_if_false: Route to thick-wall pressure design (not yet implemented)
    triggers:
      - file: conditions/thin_wall_check.md

# ==========================================
# Formula References
# ==========================================

formulas:
  - id: wall_thickness
    file: formulas/wall_thickness.md
    execution_function: calculate_wall_thickness

# ==========================================
# Assumptions
# ==========================================

assumptions:
  - id: circular_pipe
    description: Pipe geometry is circular and straight.
    validation: geometry_check

  - id: internal_pressure_only
    description: Design is governed by internal pressure only.
    validation: load_case_check

# ==========================================
# Limitations
# ==========================================

limitations:
  - id: thin_wall_applicability
    parameter: geometry
    condition: Thin-wall equation applicable when t < D/6
    action: warning

# ==========================================
# Notes
# ==========================================

notes:
  - id: corrosion_allowance
    text: Corrosion allowance must be added separately to the calculated thickness for ordered wall thickness.

  - id: mill_tolerance
    text: Mill tolerance and manufacturing under-tolerance should be considered when selecting ordered pipe wall thickness.

# ==========================================
# References
# ==========================================

references:
  - node_id: B313-material-stress

# ==========================================
# Traceability
# ==========================================

trace:
  capture:
    - inputs
    - decisions
    - formulas
    - intermediate_values
    - outputs
    - warnings

# ==========================================
# Report Configuration
# ==========================================

report:
  section_title: "Wall Thickness — §304.1.1"
  include:
    - node_reference
    - paragraph_text
    - inputs
    - assumptions
    - formulas
    - decisions
    - outputs
    - warnings
  explanation_required: true

# ==========================================
# AI Guidance
# ==========================================

ai_hints:
  explanation_focus: Explain why each input is required and how the thin-wall criterion affects equation selection.
  common_questions:
    - Why is weld joint efficiency E required?
    - When does the thin-wall equation not apply?
    - How is ordered thickness different from required thickness?
  avoid:
    - Do not alter calculated thickness values.
    - Do not skip the thin-wall applicability decision in reports.

---

# Standard Paragraph Content

## Paragraph Text

> **Development sample — not verbatim standard text.**  
> Production nodes must contain the exact ASME B31.3 §304.1.1 paragraph text for audit traceability.

For straight pipe under internal pressure, the minimum required wall thickness for pressure design shall be established using the applicable pressure design equation. Where the thin-wall criterion is satisfied, the required thickness may be determined from the relationship between design pressure, outside diameter, allowable stress, and applicable design factors.

---

# Engineering Explanation

This node implements the thin-wall internal pressure thickness calculation used in piping pressure design. It is the primary calculation step for the `pipe_wall_thickness_design` workflow.

The allowable stress `S` is expected from the material stress dependency node (`B313-material-stress`). Design pressure `P` and outside diameter `D` are user inputs. Factors `E`, `W`, and `Y` follow standard pressure design practice for welded pipe.

---

# Decision Logic

This node applies when:

- The component is straight pipe or pipe fitting analyzed as pipe.
- Internal pressure governs the thickness requirement.
- The thin-wall check (`t < D/6`) is satisfied after initial thickness evaluation.

This node does not apply when:

- External pressure governs (different design provisions).
- The thick-wall equation is required (thin-wall check fails).

---

# Formula Documentation

See `formulas/wall_thickness.md` for the executable formula definition.

Display equation:

```
t = PD / 2(SEW + PY)
```

---

# Notes

- All calculation inputs are converted to SI units before execution; original user units are preserved for traceability.
- Intermediate values are not rounded during execution.
