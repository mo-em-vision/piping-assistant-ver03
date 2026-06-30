# Text Node Template

Use for initiation text, equation introductions, result explanations, and captions.

**Preferred:** embed in a parent section node under `texts:` (see [`embedded_source.md`](embedded_source.md)).

Standalone folder:

```yaml
---
id: B313-eq-2-intro
type: text
title: Equation (2) introduction
role: equation_intro
# role: initiation | equation_intro | result_explanation | caption

display_order: 10

edges:
  - to: B313-eq-2
    type: explains
---

The required thickness of straight sections of pipe shall be determined
in accordance with eq. (2).
```

Embedded in parent `node.yaml`:

```yaml
texts:
  - id: B313-eq-2-intro
    type: text
    kind: section
    role: equation_intro
    text: >
      The required thickness of straight sections of pipe shall be determined
      in accordance with eq. (2): t_m = t + c.
  - id: B313-304.1.1-init-text
    type: text
    kind: section
    role: initiation
    title: Calculation of Minimum Required Thickness
    display_order: 1
    documentation:
      description: >
        Calculation of minimum required thickness of a straight section pipe (ASME B31.3 §304.1.1).
```

Or with full `source:` block when prose is longer than a `text:` field allows.

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | Must be `text` |
| `role` | One of: `initiation`, `equation_intro`, `result_explanation`, `caption` |

## Optional fields

| Field | Description |
|-------|-------------|
| `display_order` | Sort order when multiple text blocks appear together |
| Body markdown | Human-readable content for the central panel |
