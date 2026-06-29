# Workflow Node Template

Use for task entry points / calculators. Replaces legacy `standards/tasks/*/root.md`.

```yaml
---
id: B313-WF-EXAMPLE
type: workflow
title: Example Workflow Title
version: "1.0"
status: draft
engineering_intent: example_intent

purpose: >
  Short description of what this workflow calculates or verifies.

anchors_to: B313-304.1.1
goal_output: B313-param-t_m

report:
  template: example_report
  include:
    - dependency_path
    - decisions
    - calculations
    - traceability

edges:
  - to: B313-304.1.1
    type: anchors_to
  - to: B313-304.1.1-init-text
    type: contains
---

# Workflow initiation text (optional body)

Brief overview shown when the workflow starts.
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique workflow node id (prefix `B313-WF-`) |
| `type` | Must be `workflow` |
| `title` | Display name in task catalog |
| `anchors_to` | Primary standard section node id |
| `goal_output` | Parameter node id representing the workflow goal |

## Optional fields

| Field | Description |
|-------|-------------|
| `engineering_intent` | Slug for routing and analytics |
| `report` | Report generation configuration |
| `edges` | Explicit semantic edges (compiled to graph_edges) |
