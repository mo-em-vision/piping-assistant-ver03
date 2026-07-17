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
- You need descriptive table footnote prose as separate inspectable nodes (use `table_note` per [table-note.md](table-note.md); link from this lookup via `notes:` and `has_table_note` edges).

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
  rule: by_material_temperature
  bindings:
    material_grade: PARAM-material-grade
    design_temperature: PARAM-design-temperature
returns:
  - parameter: PARAM-allowable-stress
    symbol: S
edges:
  - type: returns_parameter
    target: PARAM-allowable-stress
  - type: requires_parameter
    target: PARAM-material-grade
  - type: requires_parameter
    target: PARAM-design-temperature
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

Rule definitions (`lookup_rules`) for the named `lookup.rule` may be co-located on the lookup node or on the bound table data YAML. Full schema: [`spec/lookup_rules.md`](../../../spec/lookup_rules.md).

## 7. Required fields

| Field | Rule |
| --- | --- |
| `type` | `lookup` |
| `key` or `title` | At least one identifier |
| `name` or `title` | Human label |
| `description` or `title` | Definition |
| `table_number` | Or nested in `source.table_number`, or `table_reference` metadata |
| Table binding | `table_id`, `lookup.table`, or `reads_table` edge |
| `lookup.table` | Graph table id (required in `lookup` block) |
| `lookup.rule` | Named rule under `lookup_rules` (required) |
| `lookup.bindings` | Maps logical rule input keys → `PARAM-*` ids (required) |
| Output binding | `output_param`, `returns`, or `returns_parameter` edge |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `authority.authorized_by` | Governing paragraph ids — compiled to graph edges at load; do not author `authorized_by` in `edges` (per [01-shared-node-contract.md](01-shared-node-contract.md) §10) |
| `authority.authority_context_required` | Requires active authority context |
| `requires` | Input parameter bindings with symbols |
| `lookup_rules` | Rule specs keyed by `lookup.rule` (may be co-located or on table data YAML) |
| `source` | Pack, yaml path, tables_db reference |
| `inputs` | Legacy input descriptor list (prefer `lookup.bindings`) |
| `edges` | `requires_parameter`, `reads_table`, `returns_parameter` |
| `metadata.status` | Lifecycle |

### `lookup` block (v2)

| Field | Required | Purpose |
| --- | --- | --- |
| `lookup.table` | yes | Graph table id |
| `lookup.rule` | yes | Named rule under `lookup_rules` |
| `lookup.bindings` | yes | Logical input keys → `PARAM-*` ids |

**Forbidden in `lookup` block:** `lookup.keys` (removed in v2). Do not author `lookup.lookup_rule` — use `lookup.rule`.

### Table footnotes (`table_note` nodes)

When a lookup-backed table has numbered or lettered footnotes, author separate **`table_note`** nodes for the prose. Link them from this lookup via `notes:` aggregation and `has_table_note` edges per [table-note.md](table-note.md). Footnote nodes use `note_for_table` back to this lookup. Do not put footnote prose or alternative resolution config on the lookup node — executable resolution remains `lookup.bindings` + `lookup.rule` here.

Full binding and rule schema: [`spec/lookup_rules.md`](../../../spec/lookup_rules.md).

## 9. Forbidden fields

```text
runtime_value, fact_value, user_input, execution_id, task_id,
calculation_result, selected_for_execution, active_in_context
```

Also forbidden:

- `authorized_by` in `edges` (use top-level `authority.authorized_by`)
- `calculates_parameter` edges (use `returns_parameter`)
- `lookup.keys` in the `lookup` block (deprecated; use `lookup.bindings`)
- Top-level `links` block

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `reads_table` | table / self id | Table data source |
| `requires_parameter` | `PARAM-*` | Lookup keys |
| `returns_parameter` | `PARAM-*` | Resolved output |
| `has_table_note` | `table_note` id | Footnote linkage — see [table-note.md](table-note.md) |
| Other taxonomy edges | per validator | Excluding `authorized_by` in `edges` |

## 11. Fields consumed by runtime components

Lookup executor reads `lookup.table`, `lookup.rule`, and `lookup.bindings` to resolve rule inputs from task Facts and load the matching `lookup_rules` entry. Graph expansion activates lookups on the expanded path and treats bound `PARAM-*` nodes as lookup keys. Execution writes derived Facts for `returns` / `returns_parameter` outputs. Presentation may render future table/lookup blocks from lookup metadata.

## 12. Validation procedure

1. Parse YAML frontmatter.
2. Run `validate_lookup_node(meta)` from `engine/validation/lookup_node_validator.py` (includes `validate_lookup_config` from `engine/validation/lookup_rule_validator.py`).
3. Confirm table binding via `table_id`, `lookup.table`, or `reads_table` edge.
4. Confirm `lookup.rule` and `lookup.bindings` are present and binding keys cover the selected rule's strategy inputs.
5. Confirm output via `returns`, `output_param`, or `returns_parameter` edge.
6. Validate edges; reject `calculates_parameter`.
7. Rebuild standards DBs when table data changes.

## 13. Common authoring mistakes

- Using `calculates_parameter` instead of `returns_parameter`.
- Omitting `table_number` when no `reads_table` edge or `lookup.table` is present.
- Modeling validation checks as lookups.
- Storing resolved table cell values on the node.
- Authoring `lookup.keys` instead of `lookup.bindings` and `lookup.rule`.
- Binding keys in `lookup.bindings` that do not match the selected rule's strategy inputs.
- Putting `authorized_by` in `edges` instead of `authority.authorized_by`.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-1.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-2.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3C.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-5-1.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/lookup_node_validator.py` — `validate_lookup_node`, `_has_edge`
- Lookup rule config: `engine/validation/lookup_rule_validator.py` — `validate_lookup_config`, `validate_lookup_bindings` (`lookup.keys` → deprecated error)
- Spec: [`spec/lookup_rules.md`](../../../spec/lookup_rules.md) — v2 `lookup_rules` schema and binding rules
- Table reference: `engine/reference/table_metadata.py` — `table_reference`
- Edge validation: `engine/reference/graph_compile.py` — `validate_edge_item`
