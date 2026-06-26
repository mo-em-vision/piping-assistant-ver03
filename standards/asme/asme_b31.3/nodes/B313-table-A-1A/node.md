---
id: B313-table-A-1A
type: lookup
title: Table A-1A — Quality Factors (Seamless Pipe)
version: "1.0"
status: draft
paragraph: "Appendix A, Table A-1A"
section: "Appendix A"
topic: quality_factor

depends_on: []

inputs:
  - id: material
    name: material
    description: Pipe material specification
    required: true
    source: user_input
    unit: dimensionless

  - id: joint_category
    name: joint_category
    description: Pipe or joint category
    required: true
    source: user_input
    unit: dimensionless

outputs:
  - id: quality_factor
    name: E
    description: Quality factor
    unit: dimensionless
    type: quantity

lookups:
  - id: appendix_a1a_quality
    source: table
    table_id: asme_b31.3_A-1A
    lookup_rule: material_and_joint_category
---

# Table A-1A — Quality Factors for Seamless Pipe

> **Development sample — not verbatim ASME B31.3 table data.**

Lookup for quality factor **E** by material and joint category. Data is stored in `asme_b313_tables.db` (`table_id: asme_b31.3_A-1A`).
