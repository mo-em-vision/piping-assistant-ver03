---
# ==========================================
# Node Identity
# ==========================================

id: B313-304.1.1
type: definition
title: Required Thickness and Nomenclature for Straight Pipe
version: "2016"
status: draft
created: "2026-06-17"
modified: "2026-06-19"

# ==========================================
# Standard Context
# ==========================================

paragraph: "304.1.1"
section: "304 Pressure Design of Components"
topic: pipe_wall_thickness
revision_year: 2024
display_heading: >
  Calculation of Minimum Required Thickness of a straight section pipe
  (according to ASME B 31.3 paragraph 304.1.1)

# ==========================================
# Purpose
# ==========================================

purpose: >
  Establish the minimum required thickness for straight sectioned pipe according to ASME B31.3.
engineering_intent: pipe_wall_thickness_design

# ==========================================
# Dependencies
# ==========================================

depends_on:
  - node_id: B313-304.1.2
    dependency_type: calculation
    when:
      field: pressure_loading
      in: [internal_pressure]
  - node_id: B313-304.1.3
    dependency_type: calculation
    when:
      field: pressure_loading
      in: [external_pressure]

# ==========================================
# Assumptions
# ==========================================

assumptions:
  - id: straight_pipe_section
    field: straight_pipe_section
    description: >
      Applied to a straight section of a pipe.
    required_for_expansion: true
    requires_confirmation: true
    allowed_values: [true, false]
    blocks_expansion_on: [false]
    expansion_block_message: >
      Non-straight pipe sections are not yet supported. A future node will cover fittings and bends.

interactions:
  - variable: pressure_loading
    mode: decision
    required: true
    required_for_expansion: true
    options:
      - internal_pressure
      - external_pressure
    aliases:
      internal: internal_pressure
      internal_pressure: internal_pressure
      internal pressure: internal_pressure
      internally_pressurized: internal_pressure
      external: external_pressure
      external_pressure: external_pressure
      external pressure: external_pressure
      externally_pressurized: external_pressure
    question: >
      Is the pipe subjected to internal or external pressure?
      Internal pressure design uses §304.1.2; external pressure design uses §304.1.3.
      Coefficients E, S, W, and Y are defined in §304.1.1(b).

# ==========================================
# Subsections
# ==========================================

subsections:
  - id: a
    label: "(a)"
    text: >
      The required thickness of straight sections of pipe shall be determined
      in accordance with eq. (2).
    equations:
      - id: eq-2
        display: "t_m = t + c"
        description: Minimum required thickness equals pressure design thickness plus corrosion allowance.
        file: equations/eq_2_minimum_required_thickness.md
        execution_function: calculate_minimum_required_thickness
    additional_text: >
      The minimum thickness, T, for the pipe selected, considering
      manufacturer's minus tolerance, shall be not less than t_m.

  - id: b
    label: "(b)"
    text: >
      The following nomenclature is used in the equations for pressure design
      of straight pipe:

# ==========================================
# Nomenclature
# ==========================================

nomenclature:
  - symbol: c
    input_id: corrosion_allowance
    introduced_here: true
    unit: mm
    allowed_units: [mm, in]
    description: >
      Sum of the mechanical allowances (thread or groove depth) plus corrosion and
      erosion allowances. For threaded components, the nominal thread depth
      (dimension h of ASME B1.20.1, or equivalent) shall apply. For machined
      surfaces or grooves where the tolerance is not specified, the tolerance
      shall be assumed to be 0.5 mm (0.02 in.) in addition to the specified
      depth of the cut.
    references:
      - standard: ASME B1.20.1
    defaults:
      - value: 0.5
        unit: mm
        condition: >
          machined surfaces or grooves where tolerance is not specified
        requires_confirmation: true

  - symbol: D
    input_id: outside_diameter
    introduced_here: true
    description: >
      Outside diameter of pipe as listed in tables of standards or
      specifications or as measured.
    unit: mm
    allowed_units: [mm, in]
    references:
      - standard: asme_b36.10
        table: tables/welded_seamless_pipe_dimensions.yaml
        field: outside_diameter_mm
    resolution:
      method: table_lookup
      keys: [nominal_pipe_size]
      table: standards/asme/asme_b36.10/tables/welded_seamless_pipe_dimensions.yaml
      node_id: asme_b36.10
  - symbol: d
    description: Inside diameter of pipe.
    references:
      - paragraph: "304.1.1(b)"

  - symbol: E
    input_id: weld_joint_efficiency
    introduced_here: true
    description: Quality factor from Tables A-1A and A-1B.
    references:
      - paragraph: "304.1.1(b)"
      - table: "Table A-1A"
        table_id: asme_b31.3_A-1A
        node_id: B313-table-A-1A
      - table: "Table A-1B"
        table_id: asme_b31.3_A-1B
        node_id: B313-table-A-1B
    resolution:
      - method: table_lookup
        keys: [material, joint_category]
        tables:
          - A-1A
          - A-1B

  - symbol: P
    input_id: design_pressure
    introduced_here: true
    description: Internal design gage pressure.
    references:
      - paragraph: "304.1.1(b)"
    resolution:
      method: user_input
      required_when_nodes: [B313-304.1.2]

  - symbol: S
    input_id: allowable_stress
    introduced_here: true
    description: Stress value from Table A-1.
    references:
      - paragraph: "304.1.1(b)"
      - table: "Table A-1"
        table_id: asme_b31.3_A-1
        node_id: B313-table-A-1
      - node_id: B313-table-A-1

  - symbol: T
    description: >
      Pipe wall thickness, manufacturing tolerance considered.
    references:
      - paragraph: "304.1.1(b)"
      - paragraph: "304.1.1(a)"

  - symbol: t
    description: >
      Pressure design thickness, as calculated in accordance with para. 304.1.2
      for internal pressure or as determined in accordance with para. 304.1.3
      for external pressure.
    references:
      - paragraph: "304.1.1(b)"
      - paragraph: "304.1.2"
      - paragraph: "304.1.3"
      - node_id: B313-304.1.2
      - node_id: B313-304.1.3

  - symbol: t_m
    description: Minimum required thickness (t + c).
    references:
      - paragraph: "304.1.1(b)"
      - paragraph: "304.1.1(a)"
      - equation: "eq-2"

  - symbol: W
    input_id: weld_strength_reduction
    introduced_here: true
    description: Weld strength reduction factor per para. 302.3.5(e).
    references:
      - paragraph: "304.1.1(b)"
      - paragraph: "302.3.5(e)"
        node_id: B313-302.3.5
        subsection: e
    resolution:
      method: table_lookup
      keys: [material, design_temperature, weld_joint_category]
      table_id: asme_b31.3_302.3.5
      node_id: B313-table-302-3-5
      subsection: e

  - symbol: Y
    input_id: temperature_coefficient
    introduced_here: true
    description: >
      Coefficient from Table 304.1.1 when t < D/6 (interpolate for intermediate
      temperatures). When t >= D/6: Y = (d + 2c) / (D + d + 2c).
    references:
      - paragraph: "304.1.1(b)"
      - table: "Table 304.1.1"
        table_id: asme_b31.3_table_304_1_1
        node_id: B313-table-304-1-1
    resolution:
      - when: { field: thin_wall, in: [true] }
        method: table_lookup
        table_id: asme_b31.3_table_304_1_1
        key: design_temperature
        interpolation: true
      - when: { field: thin_wall, in: [false] }
        method: equation
        expression: "(d + 2*c) / (D + d + 2*c)"
        file: ../304.1.2/equations/thick_wall_y.md

# ==========================================
# Equation References
# ==========================================

equations:
  - id: eq-2
    file: equations/eq_2_minimum_required_thickness.md
    execution_function: calculate_minimum_required_thickness

# ==========================================
# References
# ==========================================

references:
  - node_id: B313-304.1.2
    reason: Pressure design thickness t for internal pressure is calculated per §304.1.2.
  - node_id: B313-304.1.3
    reason: Pressure design thickness t for external pressure is determined per §304.1.3.

# ==========================================
# Traceability
# ==========================================

trace:
  capture:
    - paragraph_text
    - nomenclature

# ==========================================
# Report Configuration
# ==========================================

report:
  section_title: "Required Thickness and Nomenclature — §304.1.1"
  include:
    - node_reference
    - paragraph_text
    - nomenclature
  explanation_required: true

# ==========================================
# AI Guidance
# ==========================================

ai_hints:
  explanation_focus: >
    Explain the difference between t (pressure design thickness), c (allowances),
    t_m (minimum required thickness), and T (selected pipe wall thickness).
  common_questions:
    - What is the difference between t and t_m?
    - What does the corrosion allowance c include?
    - Why must selected thickness T be not less than t_m?
  avoid:
    - Do not confuse t_m with the calculated t from §304.1.2 without adding c.
    - Do not omit manufacturer's minus tolerance when discussing T.

---

# ASME B31.3 §304.1.1

## (a)

The required thickness of straight sections of pipe shall be determined in accordance with eq. (2):

```
$$
t_m = t + c
\tag{2}
$$
```

The minimum thickness, **T**, for the pipe selected, considering manufacturer's minus tolerance, shall be not less than **t_m**.

## (b)

The following nomenclature is used in the equations for pressure design of straight pipe:


| Symbol  | Description                                                                                                                                                                                                                                                                                                                                                                               |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **c**   | sum of the mechanical allowances (thread or groove depth) plus corrosion and erosion allowances. For threaded components, the nominal thread depth (dimension h of ASME B1.20.1, or equivalent) shall apply. For machined surfaces or grooves where the tolerance is not specified, the tolerance shall be assumed to be 0.5 mm (0.02 in.) in addition to the specified depth of the cut. |
| **D**   | outside diameter of pipe as listed in tables of standards or specifications or as measured                                                                                                                                                                                                                                                                                                |
| **d**   | inside diameter of pipe. For pressure design calculation, the inside diameter of the pipe is the maximum value allowable under the purchase specification.                                                                                                                                                                                                                                |
| **E**   | quality factor from [Table A-1A](table:asme_b31.3_A-1A) or [Table A-1B](table:asme_b31.3_A-1B)                                                                                                                                                                                                                                                                                            |
| **P**   | internal design gage pressure                                                                                                                                                                                                                                                                                                                                                             |
| **S**   | stress value for material from [Table A-1](table:asme_b31.3_A-1)                                                                                                                                                                                                                                                                                                                          |
| **T**   | pipe wall thickness (measured or minimum in accordance with the purchase specification)                                                                                                                                                                                                                                                                                                   |
| **t**   | pressure design thickness, as calculated in accordance with [para. 304.1.2](node:B313-304.1.2) for internal pressure or as determined in accordance with [para. 304.1.3](node:B313-304.1.3) for external pressure                                                                                                                                                                         |
| **t_m** | minimum required thickness, including mechanical, corrosion, and erosion allowances                                                                                                                                                                                                                                                                                                       |
| **W**   | weld joint strength reduction factor in accordance with [para. 302.3.5(e)](node:B313-302.3.5/e)                                                                                                                                                                                                                                                                                           |
| **Y**   | coefficient from [Table 304.1.1](table:asme_b31.3_table_304_1_1), valid for t < D/6 and for materials shown. The value of Y may be interpolated for intermediate temperatures. For t ≥ D/6: Y=(d + 2c)/(D + d + 2c)                                                                                                                                                                       |


---

# Engineering Explanation

This node records the governing thickness relationship and symbol definitions for straight-pipe pressure design. Equation (2) defines **t_m** as the sum of pressure design thickness **t** (from §304.1.2) and total allowances **c**.

The selected pipe wall thickness **T** must account for manufacturing under-tolerance and still meet or exceed **t_m**.

---

# Related Provisions

- for internally pressurized pipes the minimum pipe thickness **t** is calculated in [§304.1.2](node:B313-304.1.2).
- For externally pressurized pipes the minimum pipe wall thickness **t** is calculated in [§304.1.3](node:B313-304.1.3).
- Allowable stress **S** is obtained from [Table A-1](node:B313-table-A-1).

