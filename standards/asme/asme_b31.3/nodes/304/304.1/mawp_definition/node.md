---
id: B313-MAWP-DEFINITION
type: definition
title: Maximum Allowable Working Pressure — Definition and Nomenclature
version: "1.0"
status: draft
created: "2026-06-28"
modified: "2026-06-28"

paragraph: "304.1.2"
section: "304 Pressure Design of Components"
topic: mawp_design
revision_year: 2024
display_heading: >
  This workflow guides you through calculating the Maximum Allowable Working
  Pressure (MAWP) of piping components according to ASME B31.3.

purpose: >
  Define inputs, assumptions, and nomenclature for MAWP calculation of straight
  pipe under internal pressure per §304.1.2.
engineering_intent: mawp_design

depends_on:
  - node_id: B313-MAWP-PRESSURE-DESIGN
    dependency_type: calculation
  - node_id: B313-MAWP-CALCULATION
    dependency_type: calculation

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
  - variable: geometry_input_mode
    mode: decision
    options: [nps_and_schedule, direct_od_and_thickness]
    default: nps_and_schedule
    required: true
    confirmation_required: false
    question: >
      Provide geometry by nominal pipe size and schedule (looked up per ASME B36.10)
      or enter the outside diameter and actual wall thickness directly?

  - variable: joint_category
    mode: decision
    options: [seamless, erw, furnace_butt_welded, forging]
    default: seamless
    required: true
    confirmation_required: true
    question: >
      Confirm the pipe/joint category for quality factor E lookup (Tables A-1A and A-1B).
      Default is seamless pipe.

nomenclature:
  - symbol: t_actual
    input_id: actual_wall_thickness
    introduced_here: true
    description: Actual or ordered wall thickness of the pipe.
    unit: mm
    allowed_units: [mm, in]
    references:
      - standard: asme_b36.10
        table: tables/welded_seamless_pipe_dimensions.yaml
        field: wall_thickness_mm

  - symbol: c
    input_id: corrosion_allowance
    introduced_here: true
    unit: mm
    allowed_units: [mm, in]
    description: >
      Sum of mechanical allowances plus corrosion and erosion allowances per §304.1.1(b).

  - symbol: t
    description: Pressure design thickness (t_actual minus corrosion allowance).
    references:
      - paragraph: "304.1.1(b)"
      - node_id: B313-MAWP-PRESSURE-DESIGN

  - symbol: D
    input_id: outside_diameter
    introduced_here: true
    description: Outside diameter of pipe as listed in standards or as measured.
    unit: mm
    allowed_units: [mm, in]
    references:
      - standard: asme_b36.10

  - symbol: S
    input_id: allowable_stress
    introduced_here: true
    description: Stress value from Table A-1.
    references:
      - node_id: B313-table-A-1

  - symbol: E
    input_id: weld_joint_efficiency
    introduced_here: true
    description: Quality factor from Tables A-1A and A-1B.

  - symbol: W
    input_id: weld_strength_reduction
    introduced_here: true
    description: Weld strength reduction factor per para. 302.3.5(e).

  - symbol: Y
    input_id: temperature_coefficient
    introduced_here: true
    description: Coefficient from Table 304.1.1 when t < D/6.

  - symbol: MAWP
    description: Maximum Allowable Working Pressure.
    references:
      - paragraph: "304.1.2"
      - node_id: B313-MAWP-CALCULATION

subsections:
  - id: a
    label: "(a)"
    text: >
      Pressure design thickness is obtained from actual or ordered wall thickness
      minus corrosion allowance: t = t_actual - c.
    equations:
      - id: pressure_design_thickness
        display: "t = t_actual - c"
        description: Pressure design thickness from actual thickness minus corrosion.
        file: equations/pressure_design_thickness.md
        execution_function: calculate_pressure_design_thickness

  - id: b
    label: "(b)"
    text: >
      Maximum Allowable Working Pressure for straight pipe under internal pressure
      is calculated per §304.1.2 thin-wall equation rearranged for MAWP.
    equations:
      - id: mawp_pressure
        display: "MAWP = 2SEWt / (D - 2Yt)"
        description: Maximum Allowable Working Pressure from known thickness.
        file: ../304.1.2/equations/mawp_pressure.md
        execution_function: calculate_mawp
---

# Maximum Allowable Working Pressure — Definition

This workflow guides you through calculating the Maximum Allowable Working
Pressure (MAWP) of piping components according to ASME B31.3.

## Governing relationships

1. Pressure design thickness: `t = t_actual - c`
2. Maximum Allowable Working Pressure: `MAWP = 2SEWt / (D - 2Yt)`
