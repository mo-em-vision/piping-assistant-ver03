---
id: ASTM-a105-material-properties
type: lookup
title: ASTM A105 — Material Properties
version: "1.0"
status: draft
paragraph: "ASTM A105/A105M"
section: "Material Properties"
topic: material_properties

depends_on: []

inputs:
  - id: grade
    name: grade
    description: ASTM A105 or alias (A105, SA-105)
    required: true
    source: user_input
    unit: dimensionless

outputs:
  - id: material_properties
    name: material_properties
    description: Catalog metadata for ASTM A105 forgings
    unit: dimensionless
    type: structured

lookups:
  - id: a105_material_catalog
    source: table
    table_id: astm_a105_material_properties
    lookup_rule: grade
---

# ASTM A105 — Material Properties

Catalog entry for **ASTM A105** carbon steel forgings for piping applications.
