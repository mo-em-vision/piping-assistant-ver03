# Interaction Node Template

Path decisions that control conditional graph expansion.

**Preferred:** embed in a parent `definition` node under `interactions:` (see [`embedded_source.md`](embedded_source.md)).

Standalone folder (legacy):

```yaml
---
id: B313-interaction-pressure-loading
type: parameter
kind: interaction
input_id: pressure_loading
mode: decision
title: Pressure loading case

required: true
required_for_expansion: true

options:
  - internal_pressure
  - external_pressure

aliases:
  internal: internal_pressure
  externally_pressurized: external_pressure

question: >
  Is the pipe subjected to internal or external pressure?

edges:
  - to: B313-304.1.2
    type: next_step
    when:
      field: pressure_loading
      in: [internal_pressure]
  - to: B313-304.1.3
    type: next_step
    when:
      field: pressure_loading
      in: [external_pressure]
```

Embedded in parent `node.yaml`:

```yaml
interactions:
  - id: B313-interaction-pressure-loading
    type: parameter
    kind: interaction
    input_id: pressure_loading
    mode: decision
    required_for_expansion: true
    options: [internal_pressure, external_pressure]
    question: >
      Is the pipe subjected to internal or external pressure?
    edges:
      - to: B313-304.1.2
        type: next_step
        when: {field: pressure_loading, in: [internal_pressure]}
      - to: B313-304.1.3
        type: next_step
        when: {field: pressure_loading, in: [external_pressure]}
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | `parameter` (canonical); legacy `interaction` normalizes to this |
| `kind` | Must be `interaction` |
| `input_id` | Task state field name (legacy `field` also accepted) |
| `mode` | `decision` for branching |
| `options` | Allowed values |
| `question` | User prompt |

## Conditional edges

Use `when:` on `next_step` edges to activate branches based on task inputs.
