---
id: ASTM-a312-material-properties
type: lookup
title: ASTM A312 — Material Properties
version: "1.0"
status: draft
paragraph: "ASTM A312/A312M"
section: "Material Properties"
topic: material_properties

depends_on: []

inputs:
  - id: grade
    name: grade
    description: ASTM A312 TP grade or alias (e.g. TP316L, 316L)
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
  - id: a312_material_catalog
    source: table
    table_id: astm_a312_material_properties
    lookup_rule: grade
---

# ASTM A312 — Material Properties

> **Development reference data — verify against licensed ASTM A312/A312M for production use.**

Lookup for austenitic stainless steel pipe TP grades (TP304, TP316L, TP321, etc.), including chemical composition limits and minimum mechanical properties. Data is stored in `standards_tables.db` (`table_id: astm_a312_material_properties`).
