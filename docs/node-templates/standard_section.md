# Standard Section Node Template

Use for paragraph anchors from engineering standards (e.g. ASME B31.3 §304.1.1).

**Current authoring:** use `type: definition` or `type: calculation` with `node.yaml` + `node.md`. Legacy `type: standard_section` normalizes to `text` + `kind: section` at compile time.

## Definition node (§304.1.1 pattern)

```yaml
---
id: B313-304.1.1
type: definition
title: Required Thickness and Nomenclature for Straight Pipe

paragraph: "304.1.1"
section: "304 Pressure Design of Components"
topic: pipe_wall_thickness
revision_year: 2024

contains:
  - B313-eq-2
  - B313-interaction-pressure-loading
  - B313-assumption-straight-pipe
  - B313-304.1.1-init-text

assumptions: [...]
interactions: [...]
equations: [...]
texts: [...]

defines:
  - B313-param-c
  - B313-param-D
---

# ASME B31.3 §304.1.1
```

Pair with `node.md` for full paragraph text and embedded child `source:` blocks. See [`embedded_source.md`](embedded_source.md).

## Calculation node (§304.1.2 pattern)

```yaml
---
id: 304.1.2-a
type: calculation
title: Straight Pipe Under Internal Pressure
paragraph: "304.1.2"
revision_year: 2024

depends_on:
  - node_id: B313-304.1.1
    dependency_type: reference

contains:
  - B313-eq-wall-thickness

requires:
  - B313-param-P
  - B313-param-D

calculates:
  - B313-param-t
---
```

## Legacy `standard_section` (deprecated)

```yaml
---
id: B313-304.1.1
type: standard_section
title: Required Thickness and Nomenclature for Straight Pipe
paragraph: "304.1.1"
section: "304 Pressure Design of Components"
topic: pipe_wall_thickness
revision_year: 2024
---
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | `definition`, `calculation`, or legacy `standard_section` |
| `paragraph` | Standard paragraph reference |
| `section` | Parent section title |
