# Designation Node Template

Represents an **engineering designation** — a named classification, not a physical quantity.

Examples: NPS, DN, pipe schedule, material grade, flange rating.

```yaml
---
id: B313-designation-nps
type: designation
name: Nominal Pipe Size
symbol: NPS
description: >
  Pipe size designation per ASME B36.10 — not a physical quantity.
---
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id (prefix `B313-designation-`) |
| `type` | Must be `designation` |
| `name` | Human-readable designation name |
| `symbol` | Standard abbreviation (e.g. `NPS`, `DN`) |

## Optional fields

| Field | Description |
|-------|-------------|
| `description` | Engineering definition |

## Must NOT contain

| Field | Reason |
|-------|--------|
| `value` | Runtime selections belong in Workflow State |
| `user_input` | Collected via linked `parameter` nodes |
| `dimension` | Designations are not physical quantities |

## Relationship to parameters

Link from parameter → designation:

```yaml
references:
  - B313-designation-nps
```

The parameter retains `input_id`, `question`, and `resolution`; the designation node defines the engineering concept.

## When to use designation vs quantity

| Example | Node type |
|---------|-----------|
| Nominal Pipe Size (NPS 4) | `designation` |
| Outside diameter (114.3 mm) | `quantity` (`dimension: length`) |
| Pipe schedule (Sch 40) | `designation` |
| Wall thickness (6.02 mm) | `quantity` (`dimension: length`) |
