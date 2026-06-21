---
id: B313-304.1.3
type: calculation
title: Required Thickness Under External Pressure
version: "1.0"
status: draft
created: "2026-06-18"
modified: "2026-06-19"

paragraph: "304.1.3"
section: "304 Pressure Design of Piping Components"
topic: external_wall_thickness

purpose: >
  Determine required wall thickness for straight pipe under external pressure.
  Full calculation is not yet implemented; this node records the selected
  external-pressure design path.
engineering_intent: pipe_wall_thickness_design

depends_on:
  - node_id: B313-material-stress
    dependency_type: calculation
  - node_id: B313-304.1.1
    dependency_type: reference

inputs:
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

  - id: external_design_pressure
    name: P_ext
    description: External design pressure
    required: true
    source: user_input
    unit: Pa
    allowed_units: [Pa, bar, psi]
    validation: positive
    requires_confirmation: false

outputs:
  - id: required_thickness_external
    name: t
    description: Pressure design thickness from external pressure design
    nomenclature_ref: B313-304.1.1
    unit: mm
    type: quantity
    used_by: []

equations: []

limitations:
  - id: not_yet_implemented
    parameter: calculation
    condition: External pressure wall thickness equation not yet implemented
    action: reject

report:
  section_title: "External Wall Thickness — §304.1.3"
  include:
    - node_reference
    - paragraph_text
    - inputs
    - warnings
  explanation_required: true

trace:
  capture:
    - inputs
    - warnings

---




# Straight Pipe Under External Pressure.
To determine wall thickness and stiffening requirements for straight pipe under external pressure, the procedure outlined in the BPV Code, Section VIII, Division 1, UG-28 through UG-30 shall be followed, using as the design length, L, the running centerline length between any two sections stiffened in accordance with UG-29. As an
exception, for pipe with Do/t < 10, the value of S to be used in determining Pa2 shall be the lesser of the following values for pipe material at design temperature:
(a) 1.5 times the stress value from Table A-1 or Table A-1M of this Code, or
(b) 0.9 times the yield strength tabulated in Section II, Part D, Table Y-1 for materials listed therein (The symbol Do in Section VIII is equivalent to D in this
Code.)
## Engineering Explanation

This node is the external-pressure path for pressure design thickness **t** defined in §304.1.1(b). When `pressure_loading` is confirmed as external at §304.1.1, the workflow expands this node instead of the internal pressure equation in §304.1.2.

Calculation execution is deferred until the external pressure equation and executor are implemented.

---

# Decision Logic

This node applies when:

- The component is straight pipe or pipe fitting analyzed as pipe.
- External pressure governs the thickness requirement.
- `pressure_loading` is confirmed as `external_pressure` at §304.1.1.

This node does not apply when:

- Internal pressure governs (use `B313-304.1.2`).
