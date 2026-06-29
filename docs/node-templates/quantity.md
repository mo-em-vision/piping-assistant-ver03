# Quantity Node Template

Represents a **physical engineering quantity** (pressure, temperature, diameter, stress, thickness). Quantities are immutable graph knowledge — they never hold runtime values.

```yaml
---
id: B313-quantity-pressure
type: quantity
name: Pressure
dimension: pressure
description: >
  Internal or external gage pressure used in pressure design equations.
---
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id (prefix `B313-quantity-`) |
| `type` | Must be `quantity` |
| `name` | Human-readable quantity name |
| `dimension` | Physical dimension key (e.g. `pressure`, `length`, `stress`) |

## Optional fields

| Field | Description |
|-------|-------------|
| `description` | Engineering definition for documentation and symbol tables |
| `documentation` | Longer narrative (body markdown below front matter) |

## Must NOT contain

| Field | Reason |
|-------|--------|
| `value` | Runtime values belong in Workflow State |
| `user_input` | Collected via linked `parameter` nodes |
| `runtime_unit` / `runtime_units` | Units are declared on `parameter.canonical_unit` |

## Relationship to parameters

- A **`parameter`** node binds a quantity to task state (`input_id`, `canonical_unit`, `resolution`).
- Link with a `references` edge from parameter → quantity:

```yaml
references:
  - B313-quantity-pressure
```

- Equations `require` **parameter** nodes (not quantity nodes directly). Use relationship metadata on the `requires` entry for alias/role:

```yaml
requires:
  - node_id: B313-param-P
    priority: 40
    alias: P
    role: Internal Pressure
    displayName: Design pressure
```

## When to use quantity vs parameter vs designation

| Concept | Node type |
|---------|-----------|
| Physical measurable (P, D, S, t) | `quantity` + linked `parameter` |
| Engineering designation (NPS, schedule, flange rating) | `designation` + linked `parameter` |
| Task field binding, prompts, resolution | `parameter` only |
