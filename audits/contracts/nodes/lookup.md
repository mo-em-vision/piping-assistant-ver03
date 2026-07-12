# Lookup Node Contract

## 1. Purpose

A lookup node defines how authoritative table data is resolved into one or more parameter values given input key parameters.

## 2. Use this node when

- A standards table (allowable stress, quality factor, Y coefficient) supplies a parameter value.
- Resolution keys are other `PARAM-*` fields (material grade, temperature).
- Output is written to a `PARAM-*` via `returns` or `returns_parameter`.

## 3. Do not use this node when

- You need a closed-form formula (use `equation`).
- You need pass/fail validation (use `validation_rule`).
- You only need to store static table rows without resolution logic (author table data; bind via lookup).
- You need to store the resolved numeric result (runtime Fact).

## 4. File location

`knowledge/standards/<pack>/nodes/tables/{id}.yaml`

Many table-backed nodes in the B31.3 pack use `type: lookup` in the tables folder.

## 5. ID convention

| Pattern | Example |
| --- | --- |
| Pack-scoped table id | `asme-b313-table-A-1` |
| `LOOKUP-*` prefix | Allowed for global or legacy ids |
| `table_number` | Standard table designation (`A-1`, `304.1.1-1`) |
| `key` | Machine slug (`b313_material_allowable_stress`) |

## 6. Copyable minimal YAML skeleton

```yaml
---
id: asme-b313-table-A-1
type: lookup
key: b313_table_a_1
name: Basic Allowable Stresses Lookup
description: Resolves allowable stress from material grade and design temperature.
table_number: A-1
lookup:
  table: asme-b313-table-A-1
  keys:
    - PARAM-material-grade
    - PARAM-design-temperature
returns:
  - parameter: PARAM-allowable-stress
    symbol: S
edges:
  - type: returns_parameter
    target: PARAM-allowable-stress
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `type` | `lookup` |
| `key` or `title` | At least one identifier |
| `name` or `title` | Human label |
| `description` or `title` | Definition |
| `table_number` | Or nested in `source.table_number`, or `table_reference` metadata |
| Table binding | `table_id`, `lookup.table`, or `reads_table` edge |
| Output binding | `output_param`, `returns`, or `returns_parameter` edge |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `authority.authorized_by` | Governing paragraphs (compiled to edges) |
| `authority.authority_context_required` | Requires active authority context |
| `requires` | Input parameter bindings with symbols |
| `lookup.keys` | Key parameter list |
| `lookup.lookup_rule` | Temperature selection, interpolation rules |
| `lookup.interpolation` | Boolean |
| `source` | Pack, yaml path, tables_db reference |
| `inputs` | Legacy input descriptor list |
| `edges` | `requires_parameter`, `reads_table`, `returns_parameter` |
| `metadata.status` | Lifecycle |

## 9. Forbidden fields

```text
runtime_value, fact_value, user_input, execution_id, task_id,
calculation_result, selected_for_execution, active_in_context
```

Also forbidden:

- `calculates_parameter` edges (use `returns_parameter`)
- Top-level `links` block

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `reads_table` | table / self id | Table data source |
| `requires_parameter` | `PARAM-*` | Lookup keys |
| `returns_parameter` | `PARAM-*` | Resolved output |
| `authorized_by` | paragraph id | Prefer `authority.authorized_by` block |
| Other taxonomy edges | per validator | |

## 11. Fields consumed by runtime components

Lookup executor reads `lookup.table`, `lookup.keys`, and `requires` to query table storage. Graph expansion activates lookups on the expanded path. Execution writes derived Facts for `returns` parameters. Presentation may render future table/lookup blocks from lookup metadata.

## 12. Validation procedure

1. Parse YAML frontmatter.
2. Run `validate_lookup_node(meta)` from `engine/validation/lookup_node_validator.py`.
3. Confirm table binding via `table_id`, `lookup.table`, or `reads_table` edge.
4. Confirm output via `returns`, `output_param`, or `returns_parameter` edge.
5. Validate edges; reject `calculates_parameter`.
6. Rebuild standards DBs when table data changes.

## 13. Common authoring mistakes

- Using `calculates_parameter` instead of `returns_parameter`.
- Omitting `table_number` when no `reads_table` edge or `lookup.table` is present.
- Modeling validation checks as lookups.
- Storing resolved table cell values on the node.
- Missing key parameters in `lookup.keys` vs `requires`.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-1.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-2.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3C.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-5-1.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/lookup_node_validator.py` — `validate_lookup_node`, `_has_edge`
- Table reference: `engine/reference/table_metadata.py` — `table_reference`
- Edge validation: `engine/reference/graph_compile.py` — `validate_edge_item`
