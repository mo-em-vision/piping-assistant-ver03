---
id: B313-table-A-1A
type: lookup
title: Table A-1A — Basic Casting Quality Factors, E_c
version: "1.0"
status: draft
paragraph: "Appendix A, Table A-1A"
section: "Appendix A"
topic: quality_factor

depends_on:
  - node_id: B313-302.3.3
    subsection: b

inputs:
  - id: material
    name: material
    description: Casting material specification (ASTM)
    required: true
    source: user_input
    unit: dimensionless

outputs:
  - id: quality_factor
    name: E_c
    description: Basic casting quality factor
    unit: dimensionless
    type: quantity

lookups:
  - id: appendix_a1a_casting_quality
    source: table
    table_id: asme_b31.3_A-1A
    lookup_rule: material
---

# Table A-1A — Basic Casting Quality Factors, E_c

These quality factors are determined in accordance with [para. 302.3.3(b)](node:B313-302.3.3/b). See also [para. 302.3.3(c)](node:B313-302.3.3/c) and [Table 302.3.3C](table:asme_b31.3_table_302_3_3C) for increased quality factors applicable in special cases. Specifications are ASTM.

Lookup for basic casting quality factor **E_c** by `base_metal_group` and material. Data is stored in `asme_b313_tables.db` (`table_id: asme_b31.3_A-1A`).
