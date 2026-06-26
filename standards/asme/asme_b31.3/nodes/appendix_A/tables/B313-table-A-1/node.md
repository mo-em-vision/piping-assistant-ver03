---
id: B313-table-A-1
type: lookup
title: Table A-1 — Allowable Stress
version: "1.0"
status: draft
created: "2026-06-17"
modified: "2026-06-17"
paragraph: "Appendix A, Table A-1"
section: "Appendix A"
topic: allowable_stress

purpose: Determine allowable stress S at design temperature for pressure design calculations.
engineering_intent: pipe_wall_thickness_design

depends_on: []

inputs:
  - id: material
    name: material
    description: Pipe material specification
    required: true
    source: user_input
    unit: dimensionless
    validation: non_empty
    requires_confirmation: false

  - id: design_temperature
    name: design_temperature
    description: Design metal temperature
    required: true
    source: user_input
    unit: F
    allowed_units: [F, C, K]
    validation: positive
    requires_confirmation: false

outputs:
  - id: allowable_stress
    name: S
    description: Allowable stress at design temperature
    unit: Pa
    type: quantity
    used_by:
      - B313-304.1.1
      - B313-304.1.2
      - B313-304.1.3

lookups:
  - id: appendix_a1_stress
    source: table
    table_id: asme_b31.3_A-1
    lookup_rule: material_and_temperature
    interpolation: true

trace:
  capture:
    - inputs
    - lookups
    - outputs
    - warnings

report:
  section_title: "Table A-1 — Allowable Stress"
  include:
    - inputs
    - lookups
    - outputs
---

# Table A-1 — Allowable Stress

> **Development sample — not verbatim ASME B31.3 table data.**

Deterministic lookup for allowable stress **S** at design temperature for the selected material. Data is stored in `asme_b313_tables.db` (`table_id: asme_b31.3_A-1`).

## Output

Allowable stress **S** in Pa, passed to dependent calculation nodes (e.g. §304.1.1, §304.1.2).
