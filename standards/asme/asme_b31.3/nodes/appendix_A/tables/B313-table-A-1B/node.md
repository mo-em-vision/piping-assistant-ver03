---
id: B313-table-A-1B
type: lookup
title: Table A-1B — Quality Factors (Welded Pipe and Forgings)
version: "1.0"
status: draft
paragraph: "Appendix A, Table A-1B"
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
  - id: appendix_a1b_quality
    source: table
    table_id: asme_b31.3_A-1B
    lookup_rule: material_and_joint_category
---

# Table A-1B — Quality Factors for Welded Pipe and Forgings

> **Development sample — not verbatim ASME B31.3 table data.**

Lookup for quality factor **E** by material and joint category. Data is stored in `asme_b313_tables.db` (`table_id: asme_b31.3_A-1B`).
