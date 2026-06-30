# Equation Node Template

Pure math node. Execution uses sympy only — no `execution_function`.

**Preferred:** embed in a parent `definition` / `calculation` node under `equations:` with a `source:` block (see [`embedded_source.md`](embedded_source.md)).

Standalone folder:

```yaml
---
id: B313-eq-2
type: equation
title: Minimum required thickness
equation_id: eq-2

sympy: "t_m = t + c"
display_latex: "t_m = t + c"

requires:
  - node_id: B313-quantity-thickness
    priority: 85
    alias: t
    role: Pressure Design Thickness
    displayName: Pressure design thickness
  - node_id: B313-quantity-thickness
    priority: 90
    alias: c
    role: Corrosion Allowance
    displayName: Corrosion allowance
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

Embedded in parent metadata:

```yaml
equations:
  - id: B313-eq-2
    type: equation
    equation_id: eq-2
    file: equations/eq_2_minimum_required_thickness.md
    display: "t_m = t + c"
    sympy: "t_m = t + c"
    requires: [...]
    calculates: [B313-param-t_m]
    explains: [B313-eq-2-intro, B313-eq-2-result]
    source: |
      ---
      equation_id: eq-2
      sympy: "t_m = t + c"
      display_latex: "t_m = t + c"
      requires: [...]
      calculates: [B313-param-t_m]
      ---
      # Minimum Required Thickness (eq. 2)
```

The `file:` path is kept as a graph alias; runtime resolves embedded `source` when the external file is absent.

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | Must be `equation` |
| `sympy` | Executable sympy expression (assignment form: `output = expr`) |
| `display_latex` | Human-readable equation for UI |
| `requires` | Quantity/designation or parameter nodes for sympy evaluation |
| `calculates` | Parameter node id(s) produced |

## `requires` entry format

Each entry is a dict:

| Field | Description |
|-------|-------------|
| `node_id` | Quantity, designation, or parameter node id |
| `alias` | Sympy variable name when it differs from parameter symbol |
| `role` | Engineering role label (e.g. Internal Pressure) |
| `displayName` | UI label for symbol tables |
| `required` | Whether the input must be resolved before evaluation |
| `priority` | Collection order tie-breaker; lower = collected earlier |

Prefer `quantity` / `designation` nodes with relationship metadata. Parameters linked via `references` supply task-state values.

Plain-string entries (`- B313-param-t`) are supported for migration; they default to priority `100`.

## Rules

- Equation nodes must NOT contain questions, table lookups, or narrative text.
- Set `priority` on each direct equation input in `requires`. Lookup-key parameters (e.g. material, NPS) keep `priority` on their parameter nodes instead.
- Link intro/result text via `explains` edges to `text` nodes.
- Link parameters via `requires` / `calculates` edges.
- `calculates` stays a plain id list (outputs, not collection order).
