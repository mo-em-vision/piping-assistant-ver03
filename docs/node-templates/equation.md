# Equation Node Template

Pure math node. Execution uses sympy only — no `execution_function`.

```yaml
---
id: B313-eq-2
type: equation
title: Minimum required thickness
equation_id: eq-2

sympy: "t_m = t + c"
display_latex: "t_m = t + c"

requires:
  - node_id: B313-param-t
    priority: 85
  - node_id: B313-param-c
    priority: 90
calculates:
  - B313-param-t_m

edges:
  - to: B313-param-t
    type: requires
  - to: B313-param-c
    type: requires
  - to: B313-param-t_m
    type: calculates
  - to: B313-eq-2-intro
    type: explains
  - to: B313-eq-2-result
    type: explains
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | Must be `equation` |
| `sympy` | Executable sympy expression (assignment form: `output = expr`) |
| `display_latex` | Human-readable equation for UI |
| `requires` | Parameter nodes needed for sympy evaluation, each with collection `priority` |
| `calculates` | Parameter node id(s) produced |

## `requires` entry format

Each entry is a dict:

| Field | Description |
|-------|-------------|
| `node_id` | Parameter node id (aliases: `id`, `to`) |
| `priority` | Collection order tie-breaker; lower = collected earlier |

Plain-string entries (`- B313-param-t`) are supported for migration; they default to priority `100`.

## Rules

- Equation nodes must NOT contain questions, table lookups, or narrative text.
- Set `priority` on each direct equation input in `requires`. Lookup-key parameters (e.g. material, NPS) keep `priority` on their parameter nodes instead.
- Link intro/result text via `explains` edges to `text` nodes.
- Link parameters via `requires` / `calculates` edges.
- `calculates` stays a plain id list (outputs, not collection order).
