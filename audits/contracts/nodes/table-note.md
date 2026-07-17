# Table Note Node Contract

## 1. Purpose

A table note node stores authoritative footnote prose for a standards lookup or table node. Parent-table membership and cross-references use **different edge types**.

## 2. Use this node when

- A standards table has numbered or lettered notes (e.g. Note (1), Note (2)(a)).
- Table row cells or descriptions reference note ids as hyperlinks.
- Note prose must be inspectable separately from the parent table metadata.
- A note cites other graph nodes (standards articles, paragraphs, parameters).

## 3. Do not use this node when

- You need official paragraph subsection text (use `paragraph` with `text.original`).
- You need workflow UI copy (use `text` with a presentation `role`).
- You need gatherable user input (use `parameter`).
- You need executable table resolution (`lookup.table`, `lookup.rule`, `lookup.bindings`, `returns`) — author a `lookup` node per [lookup.md](lookup.md). A `table_note` stores footnote prose only.

## 4. File location

`knowledge/standards/<pack>/nodes/tables/{id}.yaml`

## 5. ID convention

| Field | Rule | Example |
| --- | --- | --- |
| `id` | `{table_node_id}-note-{note_code}` | `asme-b313-table-302-3-3-1-note-2a` |
| `note_code` | Standard note label without parentheses | `1`, `2a`, `3b` |
| Parent table | Derived from `id` prefix before `-note-` | `asme-b313-table-302-3-3-1` |
| Filename | Same as `id` | `asme-b313-table-302-3-3-1-note-2a.yaml` |

Do **not** author a `table_id` field.

## 6. Copyable minimal YAML skeleton

```yaml
---
id: asme-b313-table-302-3-3-1-note-1
type: table_note
standard: asme_b31.3
source:
  pack: asme_b31.3
  yaml: nodes/tables/asme-b313-table-302-3-3-1-note-1.yaml
title: Table 302.3.3-1 — Note (1)
note_code: '1'
paragraph: Table 302.3.3-1, Note (1)
section: '302.3'
topic: quality_factor
revision_year: 2024
status: draft
text: >
  Example note prose for the parent table.
edges:
  - type: note_for_table
    target: asme-b313-table-302-3-3-1
  - type: related_to
    target: 302.3.3-c
metadata:
  last_revision: 2026-07-12
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | `{table_node_id}-note-{note_code}` |
| `type` | `table_note` |
| `note_code` | Note label (`1`, `2a`, …) |
| `title` | Display heading |
| `text` | Note prose (string or `{ original: ... }`) |
| `edges` | `note_for_table` → parent table (from id prefix) |
| `metadata.last_revision`, `metadata.edited_by` | On every edit |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `paragraph` | Citation string for hover / reference panels |
| `section`, `topic`, `revision_year`, `status` | Pack indexing |
| `standard`, `source` | Pack provenance |
| `related_to` edges | Cross-references to nodes cited in note prose only |

## 9. Forbidden patterns

- `table_id` frontmatter field
- `related_to` → parent table (use `note_for_table` instead)
- Top-level `links` block
- Engineering execution fields

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `note_for_table` | parent lookup/table id | Required — footnote belongs to this table |
| `related_to` | any other node | Optional — cited content only, not the parent table |

## 11. Parent table authoring

Parent nodes are typically `type: lookup`. Executable table resolution (`lookup.table`, `lookup.rule`, `lookup.bindings`, `returns`) is authored on that **lookup** node per [lookup.md](lookup.md). This contract governs footnote prose and parent linkage only — not lookup execution configuration.

Parent lookup nodes list notes for aggregation **and** declare `has_table_note` edges:

```yaml
notes:
  - id: note_1
    node_id: asme-b313-table-302-3-3-1-note-1
edges:
  - type: has_table_note
    target: asme-b313-table-302-3-3-1-note-1
```

Do **not** use `related_to` from the lookup to its footnote nodes.

## 12. Validation procedure

- `engine/validation/table_note_node_validator.py`
- `engine/validation/lookup_node_validator.py`

Tests: `tests/reference/test_table_note_validator.py`

## 13. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-1-note-1.yaml`
- Parent table: `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-1.yaml`
