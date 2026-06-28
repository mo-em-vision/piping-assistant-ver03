---
id: B313-MAWP-PRESSURE-DESIGN
type: calculation
title: Pressure Design Thickness from Actual Thickness
version: "1.0"
status: draft
paragraph: "304.1.1"
section: "304 Pressure Design of Components"
topic: mawp_design
engineering_intent: mawp_design

purpose: >
  Compute pressure design thickness t from actual wall thickness minus corrosion allowance.
engineering_intent: mawp_design

depends_on: []

interactions: []

inputs:
  - id: geometry_input_mode
    name: geometry_input_mode
    description: Geometry entry mode
    required: true
    source: user_input
    unit: dimensionless

  - id: nominal_pipe_size
    name: NPS
    description: Nominal pipe size for dimension lookup per ASME B36.10
    nomenclature_ref: B313-MAWP-DEFINITION
    required: true
    source: user_input
    unit: dimensionless
    validation: non_empty
    when:
      field: geometry_input_mode
      in: [nps_and_schedule]

  - id: pipe_schedule
    name: pipe_schedule
    description: Pipe schedule for wall thickness lookup per ASME B36.10
    nomenclature_ref: B313-MAWP-DEFINITION
    required: true
    source: user_input
    unit: dimensionless
    validation: non_empty
    when:
      field: geometry_input_mode
      in: [nps_and_schedule]

  - id: outside_diameter
    name: D
    description: Outside diameter of pipe
    nomenclature_ref: B313-MAWP-DEFINITION
    required: true
    source: user_input
    unit: mm
    allowed_units: [mm, in]
    validation: positive
    when:
      field: geometry_input_mode
      in: [direct_od_and_thickness]

  - id: actual_wall_thickness
    name: t_actual
    description: Actual or ordered wall thickness
    nomenclature_ref: B313-MAWP-DEFINITION
    required: true
    source: user_input
    unit: mm
    allowed_units: [mm, in]
    validation: positive
    when:
      field: geometry_input_mode
      in: [direct_od_and_thickness]

  - id: corrosion_allowance
    name: c
    description: Corrosion allowance
    nomenclature_ref: B313-MAWP-DEFINITION
    required: true
    source: user_input
    unit: mm
    allowed_units: [mm, in]
    validation: non_negative

outputs:
  - id: pressure_design_thickness
    name: t
    description: Pressure design thickness
    unit: mm
    type: quantity

equations:
  - id: pressure_design_thickness
    file: ../mawp_definition/equations/pressure_design_thickness.md
    execution_function: calculate_pressure_design_thickness

assumptions: []
conditions: []
---

# Pressure Design Thickness

Computes `t = t_actual - c` before MAWP calculation.
