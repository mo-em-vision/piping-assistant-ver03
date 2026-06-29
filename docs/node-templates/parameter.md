# Parameter Node Template

Symbol definition, resolution strategy, and user prompts.

```yaml
---
id: B313-param-material
type: parameter
symbol: material
input_id: material
title: Material

canonical_unit: UNIT-dimensionless

description: >
  Pipe material specification.

question: >
  I need the pipe material specification to look up allowable stress.

resolution:
  method: user_input

defined_in:
  - B313-304.1.1

# Optional: link parameter nodes that share the same engineering concept
# (same physical quantity, different symbols or introduction sections).
# concept_id: pipe_material_spec
```

**Collection priority** is not set on parameter nodes. Only **calculation** `equation` nodes assign priority on their `requires` entries (for evaluation order). **Lookup** equations (`kind: lookup`) need all key parameters at once and do not assign priorities.

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id (prefix `B313-param-`) |
| `type` | Must be `parameter` |
| `symbol` | Engineering symbol (e.g. `c`, `t_m`) |
| `input_id` | Task state field name |
| `description` | Symbol definition for tables |
| `defined_in` | List of section/definition node ids where this symbol is introduced |

## Resolution methods

| Method | Use when |
|--------|----------|
| `user_input` | User must supply or confirm value |
| `table_lookup` | Value from standards table via lookup equation |
| `equation` | Value from another `equation` node |
| `node_output` | Value from upstream calculation node |

## Optional fields

| Field | Description |
|-------|-------------|
| `concept_id` | Shared key when multiple parameter nodes represent the same engineering quantity (aliases / alternate symbols) |
| `question` | Prompt shown in composer |
| `canonical_unit` | Unit node id (e.g. `UNIT-Pa`) — preferred |
| `unit` | **Deprecated** — compile-time alias to `canonical_unit`; derived symbol kept for runtime compat |
| `allowed_units` | Optional list of `UNIT-*` ids; default = reachable via `converts_to` |
| `references` | External standard/table citations |

## Equation requires (priority)

On the owning **calculation** equation only:

```yaml
requires:
  - node_id: B313-param-P
    priority: 40
  - node_id: B313-param-D
    priority: 50
```

Lower `priority` values are collected earlier when preparing inputs for that equation.
