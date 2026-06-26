---
id: ASTM-a53-material-properties
type: lookup
title: ASTM A53 — Material Properties
version: "1.0"
status: draft
paragraph: "ASTM A53/A53M"
section: "Material Properties"
topic: material_properties

depends_on: []

inputs:
  - id: grade
    name: grade
    description: ASTM A53 or alias (A53, SA-53)
    required: true
    source: user_input
    unit: dimensionless

outputs:
  - id: material_properties
    name: material_properties
    description: Catalog metadata for ASTM A53 pipe
    unit: dimensionless
    type: structured

lookups:
  - id: a53_material_catalog
    source: table
    table_id: astm_a53_material_properties
    lookup_rule: grade
---

# ASTM A53 — Material Properties

Catalog entry for **ASTM A53** carbon steel pipe (Types S, E, and F).
