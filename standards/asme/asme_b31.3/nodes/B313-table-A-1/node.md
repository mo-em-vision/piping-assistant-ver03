---
id: B313-table-A-1
type: lookup
title: Table A-1 — Allowable Stress
version: "1.0"
status: draft
paragraph: "Appendix A, Table A-1"
section: "Appendix A"
topic: allowable_stress

depends_on: []

inputs:
  - id: material
    name: material
    description: Pipe material specification
    required: true
    source: user_input
    unit: dimensionless

  - id: design_temperature
    name: design_temperature
    description: Design metal temperature
    required: true
    source: user_input
    unit: F
    allowed_units: [F, C, K]

outputs:
  - id: allowable_stress
    name: S
    description: Allowable stress at design temperature
    unit: Pa
    type: quantity

lookups:
  - id: appendix_a1_stress
    source: table
    table_id: asme_b31.3_A-1
    lookup_rule: material_and_temperature
    interpolation: true
---

# Table A-1 — Allowable Stress

> **Development sample — not verbatim ASME B31.3 table data.**

Deterministic lookup for allowable stress **S** at design temperature. Data is stored in `asme_b313_tables.db` (`table_id: asme_b31.3_A-1`).
