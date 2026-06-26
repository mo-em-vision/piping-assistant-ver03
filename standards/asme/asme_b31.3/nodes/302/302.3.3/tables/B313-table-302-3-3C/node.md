---
id: B313-table-302-3-3C
type: lookup
title: Table 302.3.3C — Increased Casting Quality Factors, E_c
version: "1.0"
status: draft
paragraph: "302.3.3(c), Table 302.3.3C"
section: "302.3"
topic: quality_factor

depends_on:
  - node_id: B313-302.3.3
    subsection: c

inputs:
  - id: note_1_machining
    name: note_1_machining
    description: Note (1) — machine all surfaces per ASME B46.1 finish
    required: false
    source: user_input
    unit: dimensionless
  - id: note_2_surface_exam
    name: note_2_surface_exam
    description: Note (2)(a) or (2)(b) — surface examination performed
    required: false
    source: user_input
    unit: dimensionless
  - id: note_3_volume_exam
    name: note_3_volume_exam
    description: Note (3)(a) or (3)(b) — volumetric examination performed
    required: false
    source: user_input
    unit: dimensionless

outputs:
  - id: quality_factor
    name: E_c
    description: Increased casting quality factor from supplementary examination
    unit: dimensionless
    type: quantity

notes:
  - id: note_1
    node_id: B313-note-302-3-3C-1
  - id: note_2a
    node_id: B313-note-302-3-3C-2a
  - id: note_2b
    node_id: B313-note-302-3-3C-2b
  - id: note_3a
    node_id: B313-note-302-3-3C-3a
  - id: note_3b
    node_id: B313-note-302-3-3C-3b

lookups:
  - id: table_302_3_3c_quality
    source: table
    table_id: asme_b31.3_table_302_3_3C
    lookup_rule: examination_combination
---

# Table 302.3.3C — Increased Casting Quality Factors, E_c

Increased casting quality factors referenced from [para. 302.3.3(c)](node:B313-302.3.3/c). Data is stored in `asme_b313_tables.db` (`table_id: asme_b31.3_table_302_3_3C`).

Lookup matches the row whose supplementary examination combination corresponds to the examinations performed. Quality factors higher than those shown do not result from combining tests (2)(a) and (2)(b), or (3)(a) and (3)(b). In no case shall the quality factor exceed 1.00.

## Notes to Table 302.3.3C

- [Note (1)](node:B313-note-302-3-3C-1) — machine all surfaces to 6.3 μm Ra
- [Note (2)(a)](node:B313-note-302-3-3C-2a) — magnetic particle examination (ferromagnetic only)
- [Note (2)(b)](node:B313-note-302-3-3C-2b) — liquid penetrant examination
- [Note (3)(a)](node:B313-note-302-3-3C-3a) — ultrasonic examination
- [Note (3)(b)](node:B313-note-302-3-3C-3b) — radiographic examination
