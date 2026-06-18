---
# ==========================================
# Node Identity
# ==========================================

id: B313-material-stress
type: lookup
title: Material Allowable Stress Lookup
version: "1.0"
status: draft
created: "2026-06-17"
modified: "2026-06-17"

# ==========================================
# Standard Context
# ==========================================

paragraph: "Table A-1 (sample)"
section: "Materials — Allowable Stress"
topic: material_stress

# ==========================================
# Purpose
# ==========================================

purpose: Determine allowable stress S at design temperature for pressure design calculations.
engineering_intent: pipe_wall_thickness_design

# ==========================================
# Dependencies
# ==========================================

depends_on: []

# ==========================================
# Inputs
# ==========================================

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

# ==========================================
# Outputs
# ==========================================

outputs:
  - id: allowable_stress
    name: S
    description: Allowable stress at design temperature
    unit: Pa
    type: quantity
    used_by:
      - B313-304.1.1

# ==========================================
# Lookup References
# ==========================================

lookups:
  - id: material_stress_table
    source: table
    table: tables/material_allowable_stress.yaml
    lookup_rule: material_and_temperature
    interpolation: true

# ==========================================
# Traceability
# ==========================================

trace:
  capture:
    - inputs
    - lookups
    - outputs
    - warnings

# ==========================================
# Report Configuration
# ==========================================

report:
  section_title: "Material Allowable Stress"
  include:
    - inputs
    - lookups
    - outputs

---

# Material Allowable Stress Lookup

> **Development sample — not verbatim ASME B31.3 table data.**

This node performs a deterministic table lookup to obtain allowable stress `S` at the specified design temperature for the selected material.

## Lookup

See `tables/material_allowable_stress.yaml` for sample development values (SA-106B / A106-B).

## Output

Allowable stress `S` in Pa, passed to dependent calculation nodes (e.g. `B313-304.1.1`).
