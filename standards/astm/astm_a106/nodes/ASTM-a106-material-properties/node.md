---
id: ASTM-a106-material-properties
type: lookup
title: ASTM A106 — Material Properties
version: "1.0"
status: draft
paragraph: "ASTM A106/A106M"
section: "Material Properties"
topic: material_properties

depends_on: []

inputs:
  - id: grade
    name: grade
    description: ASTM A106 grade or alias (e.g. SA-106B, A106 Gr B)
    required: true
    source: user_input
    unit: dimensionless

  - id: test_temperature
    name: test_temperature
    description: Optional mechanical test temperature
    required: false
    source: user_input
    unit: F
    allowed_units: [F, C]

outputs:
  - id: mechanical_properties
    name: mechanical_properties
    description: Minimum specified mechanical properties
    unit: dimensionless
    type: structured

lookups:
  - id: a106_material_catalog
    source: table
    table_id: astm_a106_material_properties
    lookup_rule: grade
---

# ASTM A106 — Material Properties

> **Development reference data — verify against licensed ASTM A106/A106M for production use.**

Lookup for seamless carbon steel pipe grades **A106 Gr A**, **A106 Gr B**, and **A106 Gr C**, including chemical composition limits and minimum mechanical properties. Data is stored in `standards_tables.db` (`table_id: astm_a106_material_properties`).
