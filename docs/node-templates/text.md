# Text Node Template

Use for initiation text, equation introductions, result explanations, and captions.

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
