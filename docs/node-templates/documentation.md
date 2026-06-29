# Documentation Block Template

Structured documentation for graph nodes (Phase 7). Use a `documentation:` block in node YAML front matter. Legacy top-level fields (`purpose`, `question`, `description`, body markdown) are still lowered automatically when the block is absent or a field is empty.

```yaml
---
id: B313-param-P
type: parameter
title: Design pressure

documentation:
  title: Design pressure
  summary: Short one-line summary for lists and navigation.
  description: >
    Longer engineering definition shown in symbol tables and reports.
  beforeEnter: >
    Confirm design pressure {{P}} before proceeding.
  afterExit: >
    Design pressure recorded for downstream calculations.
  instructions: >
    To continue the calculation, I need the design pressure.
  warnings:
    - Use gage pressure per ASME B31.3 convention.
  tips:
    - Convert psi to Pa if your plant standard uses SI.
  references:
    - B313-304.1.1
  reportSummary: >
    Design pressure {{P}} used for wall thickness calculation per §304.1.2.
---
```

## Field reference

| Field (YAML) | Python / API | Description |
|--------------|--------------|-------------|
| `title` | `title` | Display title |
| `summary` | `summary` | Short summary |
| `description` | `description` | Longer narrative |
| `beforeEnter` | `before_enter` | Shown before entering the node step |
| `afterExit` | `after_exit` | Shown after leaving the node step |
| `instructions` | `instructions` | User prompts / composer text |
| `warnings` | `warnings` | List of warning strings |
| `tips` | `tips` | List of tip strings |
| `references` | `references` | Standard section or node citations |
| `reportSummary` | `report_summary` | Deterministic report narrative |

CamelCase keys in YAML are normalized to snake_case at resolve time.

## Template substitution

String fields support `{{variable}}` placeholders resolved from task state:

- `input_id` keys (e.g. `{{design_pressure}}`)
- Parameter symbols (e.g. `{{P}}`)
- Output keys when present

Unknown placeholders are left unchanged.

## Legacy lowering

When `documentation:` is omitted, the resolver maps:

| Structured | Legacy source |
|------------|---------------|
| `title` | `title`, `name` |
| `summary` | `summary`, `purpose` |
| `description` | `description`, markdown body |
| `instructions` | `instructions`, `question` |
| `references` | `references`, `defined_in` |

## Runtime exposure

Resolved documentation appears on `WorkflowState`:

- `current_documentation` — active step
- `node_documentation` — map of visited and workflow root nodes

`display_emitter` prefers resolved fields with legacy fallback for unmigrated nodes.
