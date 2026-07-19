# Table Node Contract

## 1. Purpose

A table node represents authoritative structured tabular data from a standard or specification — row/column keys, provided parameters, and storage location — consumed by lookup nodes at execution time.

## 2. Use this node when

- You are modeling a standards table as a first-class graph object with metadata separate from lookup resolution logic.
- You need to declare which parameters the table supplies and which keys are required.
- Table data is stored externally (YAML, SQLite `tables.db`).

## 3. Do not use this node when

- You only need lookup resolution logic without separate table authoring (B31.3 pack often combines both in `type: lookup` under `nodes/tables/`).
- You need to execute a formula (use `equation`).
- You need to store resolved cell values (runtime Facts).

## 4. File location

Intended path per template:

`knowledge/standards/<pack>/nodes/tables/{id}.yaml`

Note: the current B31.3 pack authors many table files as `type: lookup` rather than `type: table`. Use this contract when splitting table data from lookup logic.

## 5. ID convention

| Pattern | Example |
| --- | --- |
| Descriptive id | `TABLE-B313-allowable-stress` |
| Pack table id | `asme-b313-table-A-1` |
| `key` | Machine slug |
| `table_class` | e.g. `material_property_table` |
| `source.table_number` | Standard table number (`A-1`) |

## 6. Copyable minimal YAML skeleton

```yaml
---
id: TABLE-EXAMPLE
type: table
key: example_table
name: Example Standards Table
table_class: material_property_table
authority: AUTH-ASME-B31.3
edition: 2024
description: Example authoritative table for lookup resolution.
source:
  table_number: A-1
  source_revision_year: 2024
lookup_keys:
  - parameter: PARAM-material-grade
    role: row_key
    required: true
provided_values:
  - parameter: PARAM-allowable-stress
    dimension: DIM-pressure
data:
  storage: external_yaml
  path: standards/asme/asme_b31.3/tables/example.yaml
edges:
  - type: belongs_to_authority
    target: AUTH-ASME-B31.3
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Stable table identity |
| `type` | `table` |
| `key` | Machine key |
| `name` | Human-readable title |
| `description` | Table purpose |
| `authority` | `AUTH-*` governing source |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |

Recommended for executable tables: `lookup_keys`, `provided_values`, `data.storage`, and `belongs_to_authority` edge.

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `edition` | Authority edition |
| `table_class` | Table category |
| `provides_parameters` | Shorthand param list |
| `lookup_rules` | Strategy, input resolvers, output columns, and `row_resolution` with `interpolate_columns` / `output_columns` |
| `source.paragraph` | Citing paragraph |
| `data.path` | External data file |
| `data.storage` | `external_yaml`, `tables_db`, etc. |
| `edges` | `provides_parameter_values_for`, `requires_parameter`, `belongs_to_authority` |
| `metadata.status` | Lifecycle |

## 9. Forbidden fields

```text
runtime_value, fact_value, user_input, execution_id, task_id,
calculation_result, resolved_value, cell_value
```

Also forbidden:

- Top-level `links` block
- Embedding lookup execution logic that belongs on `lookup` nodes (prefer split)

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `belongs_to_authority` | `AUTH-*` | Ownership |
| `provides_parameter_values_for` | `PARAM-*` | Output columns |
| `requires_parameter` | `PARAM-*` | Key columns |
| `contained_by` | (reverse only) | Do not author |

Lookups consume tables via `reads_table` edges pointing at this node.

## 11. Fields consumed by runtime components

Lookup executor reads `data.path` or `tables.db` references to load tabular rows. Graph compilation indexes `lookup_keys` and `provided_values` for traceability. Table metadata feeds lookup key validation. Presentation may render table captions from linked `text` nodes.

## 12. Validation procedure

No dedicated `table_node_validator.py` exists. Validate manually:

1. Confirm `type: table` and revision metadata.
2. Confirm `authority` references an existing `AUTH-*` node.
3. Confirm `data` pointer resolves to on-disk table data.
4. Confirm a companion `lookup` node exists with `reads_table` edge when table is executable.
5. Run graph compile and lookup integration tests.

## 13. Common authoring mistakes

- Collapsing table + lookup into one file without clear separation of concerns.
- Omitting `lookup_keys` so lookups cannot validate required inputs.
- Pointing `data.path` at a non-existent file.
- Using `used_by_lookup` authoring edge on table (prefer `reads_table` from lookup).
- Storing computed cell values on the table node.

## 14. Current repository examples

Template reference (no `type: table` on disk yet):

- Example id pattern: `TABLE-B313-allowable-stress`

Related lookup-table hybrids in repo:

- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-1.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-2.yaml`

## 15. Implementation evidence appendix

- Table metadata: `engine/reference/table_metadata.py` — `table_reference`
- Embedded children: `engine/reference/embedded_nodes.py` — table container keys
- Lookup consumption: `engine/validation/lookup_node_validator.py` — `reads_table` edge check
- Type detection: `is_table_node()` in `engine/reference/node_types.py`
