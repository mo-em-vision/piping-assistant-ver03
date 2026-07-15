# Table `lookup_rules` specification (v2)

Authoritative contract for declarative table lookup behavior in Ver03.

## Principles

1. **Explicit strategy** — never infer resolution from optional field combinations.
2. **Single binding source** — `lookup.bindings` on lookup nodes maps logical rule inputs to `PARAM-*` nodes.
3. **Mandatory rule** — `lookup.rule` is required; never auto-selected.
4. **Declared resolvers** — every input names its resolver; no silent defaults.
5. **Explicit policies** — `on_no_match`, `on_multiple_matches`, and per-input `match` blocks define failure behavior.
6. **Per-output metadata** — each output declares `column` and `parameter`; no rule-root output parameter.

## Where to author

| Location | Contents |
| --- | --- |
| Table data YAML | `lookup_rules` only (e.g. B36.10 `B3610-table-2-1.yaml`) |
| Lookup node YAML | `lookup` block (`table`, `rule`, `bindings`) + `lookup_rules` when co-located |

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

    inputs:
      material_grade:
        resolver: material_catalog
      design_temperature:
        resolver: identity
        column: design_temperature
        parameter: PARAM-design-temperature
        match:
          method: linear_interpolation
          outside_range: error
          duplicate_rows: error
          missing_value: error

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
| `inputs` | Logical input keys with resolver and optional match/column |
| `outputs` | Logical output keys with `column` and `parameter` |
| `on_no_match.action` | Must be `error` |
| `on_multiple_matches.action` | Must be `error` |

### Input fields

| Field | Required | Description |
| --- | --- | --- |
| `resolver` | yes | Input normalization resolver (see below) |
| `column` | when matching rows | Table column used for row match |
| `parameter` | for temperature inputs | Bound `PARAM-*` for unit conversion / conditionals |
| `match` | for temperature inputs | Match policy block |

### Match block

| Field | Values | Description |
| --- | --- | --- |
| `method` | `exact`, `linear_interpolation` | Row selection method |
| `outside_range` | `error` | Fail when query is outside table temperature range |
| `duplicate_rows` | `error` | Fail when multiple rows match same key |
| `missing_value` | `error` | Fail when matched row column is null |

Do not silently clamp unless the governing standard requires it via `PARAM-*` `lookup_conditionals`.

### Output fields

| Field | Required | Description |
| --- | --- | --- |
| `column` | yes | Table column name |
| `parameter` | yes | Target `PARAM-*` node |

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

## Runtime flow

```
lookup node (rule + bindings)
  → resolve bindings to task Facts
  → load lookup_rules[rule] from table YAML
  → validate spec (lookup_rule_validator)
  → dispatch by strategy (lookup_rule_strategies)
  → store Facts (SourceType.TABLE_LOOKUP)
```

## Validation

- `engine/validation/lookup_rule_validator.py` — rule schema and binding coverage
- `engine/validation/lookup_node_validator.py` — requires `lookup.rule` and `lookup.bindings`

## Examples in repository

See migrated nodes under `knowledge/standards/asme/` and tests in `tests/executor/test_table_rule_lookup.py`.

## Related

- [strategies.md](./strategies.md) — strategy catalog
- `audits/contracts/nodes/lookup.md` — lookup node identity contract
