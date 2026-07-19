# Table `lookup_rules` specification (v2)

Authoritative contract for declarative table lookup behavior in Ver03.

## Principles

1. **Explicit strategy** — never infer resolution from optional field combinations.
2. **Single binding source** — `lookup.bindings` on lookup nodes maps logical rule inputs to `PARAM-*` nodes.
3. **Mandatory rule** — `lookup.rule` is required; never auto-selected.
4. **Declared resolvers** — every input names its resolver; no silent defaults.
5. **Table-owned row resolution** — `row_resolution` on table rules defines breakpoint behavior and which columns are interpolated.
6. **Per-output metadata** — each output declares `column` and `parameter`; no rule-root output parameter.

## Where to author

| Location | Contents |
| --- | --- |
| Table definition YAML (`<pack>/tables/<table_ref>.yaml`) | `lookup_rules`, `row_resolution`, `option_queries` |
| Lookup node YAML | `lookup` block (`table`, `rule`, `bindings`) and `returns` only |

**Forbidden on lookup nodes:** `lookup_rules`, `row_resolution`, `match`, `interpolation`, `interpolate_columns`.

Loader: `engine/executor/lookup_rule_schema.py` → `load_table_lookup_rules()`.

## Lookup node binding

```yaml
lookup:
  table: asme-b313-table-A-1
  rule: by_material_temperature
  bindings:
    material_grade: PARAM-material-grade
    design_temperature: PARAM-design-temperature
```

| Field | Required | Description |
| --- | --- | --- |
| `lookup.table` | yes | Graph table id |
| `lookup.rule` | yes | Named rule under `lookup_rules` |
| `lookup.bindings` | yes | Maps logical input keys → `PARAM-*` ids |

**Forbidden:** `lookup.keys` (removed in v2).

## Rule block (required shape)

```yaml
lookup_rules:
  by_material_temperature:
    strategy: material_temperature

    row_resolution:
      design_temperature:
        breakpoint_column: design_temperature
        unit: degF
        method: linear_interpolation
        outside_range: error
        duplicate_breakpoints: error
        missing_value: error
        interpolate_columns:
          - allowable_stress

    inputs:
      material_grade:
        resolver: material_catalog
      design_temperature:
        resolver: identity
        column: design_temperature
        parameter: PARAM-design-temperature

    outputs:
      allowable_stress:
        column: allowable_stress
        parameter: PARAM-allowable-stress

    on_no_match:
      action: error
    on_multiple_matches:
      action: error
```

### Required rule fields

| Field | Description |
| --- | --- |
| `strategy` | Execution strategy id (see [strategies.md](./strategies.md)) |
| `inputs` | Logical input keys with resolver and optional column |
| `outputs` | Logical output keys with `column` and `parameter` |
| `row_resolution` | Required for temperature strategies; breakpoint axis policies |
| `on_no_match.action` | Must be `error` |
| `on_multiple_matches.action` | Must be `error` |

### Row resolution block

The breakpoint axis (e.g. `design_temperature`) is separate from interpolated output columns.

**Simple form (preferred)** — shared interpolation fraction across listed columns:

| Field | Values | Description |
| --- | --- | --- |
| `breakpoint_column` | column name | Row sort key |
| `unit` | unit string | Breakpoint unit (optional) |
| `method` | `exact`, `linear_interpolation`, `lower_bound`, `upper_bound` | Axis resolution method |
| `outside_range` | `error`, `clamp_to_boundary`, `lower_bound`, `upper_bound` | Out-of-range behavior |
| `duplicate_breakpoints` | `error` | Fail on duplicate breakpoint values |
| `missing_value` | `error` | Fail when source cell is null |
| `min` / `max` | number | Optional explicit permitted range |
| `interpolate_columns` | list of column names | Columns numerically interpolated |

Columns **not** in `interpolate_columns` default to `exact` (value from matched or bracketing row).

**Per-output form** — use only when columns need different resolution on the same axis:

```yaml
row_resolution:
  design_temperature:
    breakpoint_column: design_temperature
    method: linear_interpolation
    output_columns:
      allowable_stress:
        method: linear_interpolation
        unit: psi
      material_group:
        method: exact
```

Use **either** `interpolate_columns` **or** `output_columns`, not both.

Interpolation is disabled unless a column is explicitly listed with `linear_interpolation`.

### Input fields

| Field | Required | Description |
| --- | --- | --- |
| `resolver` | yes | Input normalization resolver (see below) |
| `column` | when matching rows | Table column used for row match |
| `parameter` | for temperature inputs | Bound `PARAM-*` for unit conversion |

**Forbidden on inputs:** `match` block (moved to `row_resolution`).

### Output fields

| Field | Required | Description |
| --- | --- | --- |
| `column` | yes | Table column name |
| `parameter` | yes | Target `PARAM-*` node |

## Runtime flow

```
lookup node (rule + bindings)
  → resolve bindings to task Facts
  → load lookup_rules[rule] from table definition YAML
  → validate spec (lookup_rule_validator)
  → dispatch by strategy (lookup_rule_strategies)
  → resolve_table_rows (single bracketing pass, shared fraction)
  → store Facts (SourceType.TABLE_LOOKUP) with per-column provenance
```

Resolver: `engine/executor/table_resolver.py` → `resolve_table_rows()`.

### Provenance (`TableRuleLookupResult.meta`)

Shared: `breakpoint_column`, `query_value`, `interpolation_fraction`, `lower_source_row`, `upper_source_row`, `interpolated`.

Per column (`column_provenance`): `source_column`, `source_values`, `interpolation_fraction`, `unit`, `resolution_method`, `interpolated`.

## Resolvers

| Resolver | Purpose |
| --- | --- |
| `material_catalog` | Resolve material grade to table `material_id` key |
| `metallurgical_group_key` | Pass metallurgical group as table material group id |
| `joint_category_normalize` | Normalize pipe construction type to table category |
| `nps_key` | Normalize nominal pipe size for B36.10 lookup |
| `schedule_key` | Normalize pipe schedule label |
| `identity` | Use fact value as-is (temperature and dimensionless keys) |

Generic resolver implementations live in `engine/executor/lookup_rule_resolvers.py`.

## Validation

- `engine/validation/lookup_rule_validator.py` — rule schema and binding coverage
- `engine/validation/lookup_node_validator.py` — rejects policy fields on lookup nodes
- `engine/validation/table_definition_validator.py` — table definition `lookup_rules`

## Examples in repository

- Table definitions: `knowledge/standards/asme/asme_b31.3/tables/`
- Lookup nodes: `knowledge/standards/asme/asme_b31.3/nodes/tables/` (bindings only)
- Tests: `tests/executor/test_table_rule_lookup.py`, `tests/executor/test_table_resolver.py`

## Related

- [strategies.md](./strategies.md) — strategy catalog
- `audits/contracts/nodes/lookup.md` — lookup node identity contract
- `audits/contracts/nodes/table.md` — table definition contract
