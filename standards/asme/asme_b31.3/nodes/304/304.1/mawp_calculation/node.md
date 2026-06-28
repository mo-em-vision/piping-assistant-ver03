---
id: B313-MAWP-CALCULATION
type: calculation
title: Maximum Allowable Working Pressure Calculation
version: "1.0"
status: draft
paragraph: "304.1.2"
section: "304 Pressure Design of Components"
topic: mawp_design
engineering_intent: mawp_design

purpose: >
  Calculate Maximum Allowable Working Pressure (MAWP) for straight pipe under
  internal pressure using the thin-wall equation rearranged for known thickness.

depends_on:
  - node_id: B313-table-A-1
    dependency_type: calculation
  - node_id: B313-MAWP-PRESSURE-DESIGN
    dependency_type: calculation

interactions: []

inputs:
  - id: pressure_design_thickness
    name: t
    description: Pressure design thickness from prior calculation
    required: true
    source: node_output
    unit: mm

  - id: outside_diameter
    name: D
    description: Outside diameter of pipe
    nomenclature_ref: B313-MAWP-DEFINITION
    required: true
    source: user_input
    unit: mm
    allowed_units: [mm, in]
    validation: positive

  - id: allowable_stress
    name: S
    description: Allowable stress from Table A-1
    required: true
    source: node_output
    unit: Pa

  - id: weld_joint_efficiency
    name: E
    description: Quality factor from Tables A-1A and A-1B
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
    description: Coefficient from Table 304.1.1
    required: true
    source: resolved
    unit: dimensionless
    default: 0.4
    requires_confirmation: true

outputs:
  - id: mawp
    name: MAWP
    description: Maximum Allowable Working Pressure
    unit: Pa
    type: quantity

provisional_assumptions:
  - field: thin_wall
    default: true
    description: Assume t < D/6 until thickness is verified.

equations:
  - id: mawp_pressure
    file: ../304.1.2/equations/mawp_pressure.md
    execution_function: calculate_mawp

conditions:
  - id: thin_wall_check
    name: thin_wall_check
    expression: "t < D/6"
    description: Verify thin-wall equation applicability
    sets_field: thin_wall
    on_false: subsection_b
    result_if_true: Continue with thin-wall MAWP calculation
    result_if_false: Thick-wall MAWP not yet implemented

assumptions: []
---

# MAWP Calculation

Computes `MAWP = 2SEWt / (D - 2Yt)` per §304.1.2.
