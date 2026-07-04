# Lookup Node Template

> **Implementation:** Lookup sources under `knowledge/standards/*/nodes/tables/` and pack-specific lookup paths. Validator: [`engine/validation/lookup_node_validator.py`](../../engine/validation/lookup_node_validator.py). On-disk graph edges use taxonomy types (`authorized_by`, `requires_parameter`, `returns_parameter`, `reads_table`, …). See [`Table Node.md`](Table%20Node.md) and [`Relationship Taxonomy.md`](Relationship%20Taxonomy.md).

A Lookup node defines how authoritative table data is resolved into a Parameter value.

A Lookup consumes input Parameters through runtime Facts (lookup keys).  
It returns output Parameters through derived Facts.

For formula calculations use [`equation node.md`](equation%20node.md).  
For pass/fail checks use [`validation_rule.md`](validation_rule.md).

Do **not** author a top-level `links` metadata block — object relationships belong in typed `edges` only ([`_relationship_schema.md`](_relationship_schema.md#on-disk-rule)). **Exception:** declare governing paragraphs in `authority.authorized_by` (not in `edges`); the graph compiler emits `authorized_by` edges at build time.

```yaml
---
id: LOOKUP-B313-material-allowable-stress
type: lookup

key: b313_material_allowable_stress_lookup
name: Material Allowable Stress Lookup

description: >
  Resolves allowable stress from the active ASME B31.3 allowable stress table
  using material specification and design temperature.

authority:
  authorized_by:
    - 302.3.5-d
  authority_context_required: true

requires:
  - parameter: PARAM-material-specification
    symbol: material
    required: true

  - parameter: PARAM-design-temperature
    symbol: T
    required: true
    dimension: DIM-temperature

returns:
  - parameter: PARAM-allowable-stress
    symbol: S
    dimension: DIM-pressure

lookup:
  table: asme-b313-table-A-1
  keys:
    - PARAM-material-specification
    - PARAM-design-temperature
  lookup_rule: lower_applicable_temperature
  interpolation: false

edges:
  - type: reads_table
    target: asme-b313-table-A-1

  - type: requires_parameter
    target: PARAM-material-specification

  - type: requires_parameter
    target: PARAM-design-temperature

  - type: returns_parameter
    target: PARAM-allowable-stress

metadata:
  status: active
  version: 1
---
```

---

# Purpose

A Lookup answers:

```text
What authoritative value applies for these lookup keys?
```

Examples:

```text
allowable_stress = lookup(material, temperature)
outside_diameter = lookup(NPS, schedule)
Y coefficient = lookup(material, temperature)
```

A Lookup does not store runtime values.  
It defines how table data becomes a Fact at execution time.

---

# Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id. Use `LOOKUP-*` prefix (packs may use legacy ids during migration). |
| `type` | Must be `lookup`. |
| `key` | Machine-safe lookup key. |
| `name` | Human-readable name. |
| `description` | Stable engineering description. |
| `requires` | Input Parameters used as lookup keys. |
| `returns` | Output Parameter receiving the looked-up value. |
| `lookup` | Table reference, keys, lookup rules, interpolation policy. |
| `metadata` | Status and versioning. |

Legacy authoring may use `output_param` and `table_id` instead of `returns` / `lookup.table`; prefer the structured form above for new nodes.

---

# Lookup vs Table

| | Table (`TABLE-*`) | Lookup (`LOOKUP-*`) |
|--|-------------------|---------------------|
| Role | Stores authoritative data | Defines how to read that data |
| Edge | Target of `reads_table` | Source of `reads_table` |

Do not put lookup behavior only inside the Table.  
The Table may define default lookup rules, but the Lookup node is the executable contract.

---

# Allowed relationships

Lookup nodes may use these edge types on `edges`:

```yaml
depends_on
requires_parameter
returns_parameter
reads_table
supersedes
superseded_by
```

Governing paragraphs belong in `authority.authorized_by` — not as `authorized_by` edges.

When a lookup `depends_on` a lettered paragraph (e.g. §302.3.5-e), set `target` to the full paragraph node id (`302.3.5-e`). Do **not** add `subsection` edge metadata.

Do not use `calculates_parameter` or `references_table` on lookup nodes.

---

# Forbidden fields

Lookup nodes must not contain runtime execution values.

Forbidden:

```yaml
runtime_value:
fact_value:
user_input:
execution_id:
task_id:
calculation_result:
```

---

# Validation rules

A Lookup node is invalid if:

1. `type` is not `lookup`.
2. It has no `returns` / `output_param`.
3. It has no `lookup.table` / `table_id` / `reads_table` edge.
4. It uses `calculates_parameter` instead of `returns_parameter`.
5. It allows interpolation when the authority explicitly forbids interpolation.
6. It stores runtime values.
