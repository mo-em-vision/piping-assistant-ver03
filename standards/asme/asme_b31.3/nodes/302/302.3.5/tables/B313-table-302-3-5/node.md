---
id: B313-table-302-3-5
type: lookup
title: Table 302.3.5 — Weld Joint Strength Reduction Factor W
version: "1.0"
status: draft
paragraph: "302.3.5(e)"
section: "302.3.5"
topic: weld_strength_reduction

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

  - id: weld_joint_category
    name: weld_joint_category
    description: Weld joint category
    required: true
    source: user_input
    unit: dimensionless

outputs:
  - id: weld_strength_reduction
    name: W
    description: Weld joint strength reduction factor
    unit: dimensionless
    type: quantity

lookups:
  - id: table_302_3_5_w
    source: table
    table_id: asme_b31.3_302.3.5
    lookup_rule: material_temperature_and_category
    interpolation: true
---

# Table 302.3.5 — Weld Joint Strength Reduction Factor W

> **Development sample — placeholder for ASME B31.3 Table 302.3.5.**

Lookup for weld joint strength reduction factor **W** per §302.3.5(e). Data is stored in `asme_b313_tables.db` (`table_id: asme_b31.3_302.3.5`).
