# Standard Section Node Template

Use for paragraph anchors from engineering standards (e.g. ASME B31.3 §304.1.1).

```yaml
---
id: B313-304.1.1
type: standard_section
title: Required Thickness and Nomenclature for Straight Pipe
version: "2016"
status: draft

paragraph: "304.1.1"
section: "304 Pressure Design of Components"
topic: pipe_wall_thickness
revision_year: 2024

edges:
  - to: B313-eq-2
    type: contains
  - to: B313-interaction-pressure-loading
    type: contains
  - to: B313-param-c
    type: defines
---

# ASME B31.3 §304.1.1

Optional markdown body with standard text.
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | Must be `standard_section` |
| `paragraph` | Standard paragraph reference |
| `section` | Parent section title |
