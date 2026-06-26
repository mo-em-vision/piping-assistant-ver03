---
# ==========================================
# Node Identity
# ==========================================

id: B313-304.1.2
type: calculation
title: Internal Pressure Design of Straight Pipe
version: "2016"
status: draft
created: "2026-06-17"
modified: "2026-06-19"

# ==========================================
# Standard Context
# ==========================================

paragraph: "304.1.2"
section: "304 Pressure Design of Components"
topic: pipe_wall_thickness

# ==========================================
# Purpose
# ==========================================

purpose: >
  Calculate the pressure design thickness t for straight pipe under internal
  pressure using the thin-wall pressure design equation.
engineering_intent: pipe_wall_thickness_design

# ==========================================
# Dependencies
# ==========================================

depends_on:
  - node_id: B313-material-stress
    dependency_type: calculation
  - node_id: B313-304.1.1
    dependency_type: reference
  - node_id: B313-302.3.5
    dependency_type: reference
    subsection: e

# ==========================================
# Subsections
# ==========================================

subsections:
  - id: a
    label: "(a)"
    applies_when:
      field: thin_wall
      in: [true]
    equations: [wall_thickness]
    description: >
      For t < D/6, internal pressure design thickness using equation (3a) or (3b).
  - id: b
    label: "(b)"
    applies_when:
      field: thin_wall
      in: [false]
    status: not_implemented
    description: >
      For t >= D/6 or P/SE > 0.385, thick-wall pressure design requires special consideration.

# ==========================================
# Provisional Assumptions
# ==========================================

provisional_assumptions:
  - field: thin_wall
    default: true
    description: Assume t < D/6 until thickness is calculated.

# ==========================================
# Interactions
# ==========================================

interactions:
  - variable: d_input_mode
    mode: decision
    options: [nps_lookup, direct_od]
    default: nps_lookup
    required: true
    confirmation_required: false
    question: >
      Provide outside diameter D by nominal pipe size (NPS, looked up per ASME B36.10)
      or enter the outside diameter directly (mm or in)?

  - variable: joint_category
    mode: decision
    options: [seamless, erw, furnace_butt_welded, forging]
    default: seamless
    required: true
    confirmation_required: true
    question: >
      Confirm the pipe/joint category for quality factor E lookup (Tables A-1A and A-1B).
      Default is seamless pipe.

# ==========================================
# Inputs
# ==========================================

inputs:
  - id: design_pressure
    name: P
    description: Internal design gage pressure
    nomenclature_ref: B313-304.1.1
    required: true
    source: user_input
    unit: Pa
    allowed_units: [Pa, bar, psi]
    validation: positive
    requires_confirmation: false

  - id: nominal_pipe_size
    name: NPS
    description: Nominal pipe size for outside diameter lookup per ASME B36.10
    nomenclature_ref: B313-304.1.1
    required: true
    source: user_input
    unit: dimensionless
    validation: non_empty
    requires_confirmation: false
    when:
      field: d_input_mode
      in: [nps_lookup]

  - id: outside_diameter
    name: D
    description: Outside diameter of pipe as measured
    nomenclature_ref: B313-304.1.1
    required: true
    source: user_input
    unit: mm
    allowed_units: [mm, in]
    validation: positive
    requires_confirmation: false
    when:
      field: d_input_mode
      in: [direct_od]

  - id: corrosion_allowance
    name: c
    description: Sum of mechanical allowances per ?304.1.1(b)
    nomenclature_ref: B313-304.1.1
    required: false
    source: default
    unit: mm
    allowed_units: [mm, in]
    requires_confirmation: true

  - id: allowable_stress
    name: S
    description: Stress value from Table A-1 at design temperature
    nomenclature_ref: B313-304.1.1
    required: true
    source: node_output
    unit: Pa
    allowed_units: [Pa, psi]
    validation: positive
    requires_confirmation: false

  - id: weld_joint_efficiency
    name: E
    description: Quality factor from Tables A-1A and A-1B
    nomenclature_ref: B313-304.1.1
    required: true
    source: default
    unit: dimensionless
    default: 1.0
    requires_confirmation: true

  - id: joint_category
    name: joint_category
    description: Pipe or joint category for E lookup in Tables A-1A and A-1B
    nomenclature_ref: B313-304.1.1
    required: false
    source: user_input
    unit: dimensionless
    validation: non_empty
    requires_confirmation: false

  - id: weld_strength_reduction
    name: W
    description: Weld strength reduction factor per para. 302.3.5(e)
    nomenclature_ref: B313-304.1.1
    required: true
    source: default
    unit: dimensionless
    default: 1.0
    requires_confirmation: true

  - id: temperature_coefficient
    name: Y
    description: Coefficient from Table 304.1.1 (t < D/6) or thick-wall equation
    nomenclature_ref: B313-304.1.1
    required: true
    source: resolved
    unit: dimensionless
    default: 0.4
    requires_confirmation: true

# ==========================================
# Outputs
# ==========================================

outputs:
  - id: required_thickness
    name: t
    description: Pressure design thickness
    nomenclature_ref: B313-304.1.1
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
    sets_field: thin_wall
    on_false: subsection_b
    result_if_true: Continue with thin-wall calculation per equations/wall_thickness.md
    result_if_false: Route to thick-wall pressure design (not yet implemented)
    triggers:
      - file: conditions/thin_wall_check.md

# ==========================================
# Equation References
# ==========================================

equations:
  - id: wall_thickness
    file: equations/wall_thickness.md
    execution_function: calculate_wall_thickness

# ==========================================
# Assumptions
# ==========================================

assumptions: []

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
    text: >
      Pressure design thickness t from this node must be combined with
      allowances c per ?304.1.1 eq. (2) to obtain t_m.

  - id: mill_tolerance
    text: >
      Selected pipe wall thickness T must be not less than t_m per ?304.1.1(a),
      considering manufacturer's minus tolerance.

# ==========================================
# References
# ==========================================

references:
  - node_id: B313-material-stress
  - node_id: B313-304.1.1
  - node_id: B313-302.3.5
    subsection: e
    paragraph: "302.3.5(e)"

# ==========================================
# Traceability
# ==========================================

trace:
  capture:
    - inputs
    - decisions
    - equations
    - intermediate_values
    - outputs
    - warnings

# ==========================================
# Report Configuration
# ==========================================

report:
  section_title: "Internal Pressure Wall Thickness ? ?304.1.2"
  include:
    - node_reference
    - paragraph_text
    - inputs
    - assumptions
    - equations
    - decisions
    - outputs
    - warnings
    - nomenclature
  explanation_required: true

# ==========================================
# AI Guidance
# ==========================================

ai_hints:
  explanation_focus: >
    Explain why each input is required and how the thin-wall criterion affects
    equation selection. Use nomenclature from ?304.1.1(b) when describing symbols.
  common_questions:
    - Why is weld joint quality factor E required?
    - When does the thin-wall equation not apply?
    - How is t related to t_m and T per ?304.1.1?
  avoid:
    - Do not alter calculated thickness values.
    - Do not skip the thin-wall applicability decision in reports.
    - Do not report t as the final ordered thickness without applying ?304.1.1.

---

# ASME B31.3 Paragraph 304.1.2

## Paragraph Text

**(a)** For t < D/6, the internal pressure design thickness for straight pipe shall be not less than that calculated in accordance with either equation (3a) or equation (3b).


$$
 t = PD/2(SEW + PY)
\tag{3a}
$$



$$
t = P(d+2c)/2(SEW - P(1-Y))
\tag{3b}
$$
```


**(b)** For t ≥ D/6 or for P/SE > 0.385, calculation of pressure design thickness for straight pipe requires special consideration of factors such as theory of failure,
effects of fatigue, and thermal stress.

---

# Engineering Explanation

This node implements the thin-wall internal pressure thickness calculation for straight pipe. It produces pressure design thickness **t**, which is combined with allowances **c** in §304.1.1 to obtain **t_m**.

The allowable stress **S** is expected from the material stress dependency node (`B313-material-stress`). Design pressure **P** and outside diameter **D** are user inputs. Factors **E**, **W**, and **Y** follow the nomenclature in §304.1.1(b).

---

# Decision Logic

This node applies when:

- The component is straight pipe or pipe fitting analyzed as pipe.
- Internal pressure governs the thickness requirement.
- The thin-wall check (`t < D/6`) is satisfied after initial thickness evaluation.

This node does not apply when:

- External pressure governs (use §304.1.3).
- The thick-wall equation is required (thin-wall check fails).

---

# Equation Documentation

See `equations/wall_thickness.md` for the executable equation definition.

Display equation:

```
t = PD / 2(SEW + PY)
```

---

# Notes

- All calculation inputs are converted to SI units before execution; original user units are preserved for traceability.
- Intermediate values are not rounded during execution.
- Refer to §`B313-304.1.1` for symbol definitions and the t_m = t + c relationship.

