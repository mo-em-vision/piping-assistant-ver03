---
id: ASTM-stainless-castings-material-properties
type: lookup
title: ASTM Stainless Castings — Material Properties
version: "1.0"
status: draft
paragraph: "ASTM A351 / A451 / A487"
section: "Material Properties"
topic: material_properties

depends_on: []

inputs:
  - id: grade
    name: grade
    description: ASTM casting or centrifugal pipe specification (A351, A451, A487)
    required: true
    source: user_input
    unit: dimensionless

outputs:
  - id: material_properties
    name: material_properties
    description: Catalog metadata for stainless casting specifications
    unit: dimensionless
    type: structured

lookups:
  - id: stainless_castings_material_catalog
    source: table
    table_id: astm_stainless_castings_material_properties
    lookup_rule: grade
---

# ASTM Stainless Castings — Material Properties

Catalog entries for **ASTM A351**, **ASTM A451**, and **ASTM A487** stainless steel casting and centrifugal pipe specifications.
