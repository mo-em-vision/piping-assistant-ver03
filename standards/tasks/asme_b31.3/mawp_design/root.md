---
id: B313-MAWP-DESIGN
type: root
title: Maximum Allowable Working Pressure (MAWP)
version: "1.0"
status: draft
engineering_intent: mawp_design

purpose: >
  Entry point for calculating the Maximum Allowable Working Pressure (MAWP)
  of straight pipe under internal pressure per ASME B31.3 §304.1.2.

depends_on:
  - node_id: B313-table-A-1
    dependency_type: calculation
  - node_id: B313-MAWP-DEFINITION
    dependency_type: reference

report:
  template: mawp_design
  include:
    - dependency_path
    - decisions
    - calculations
    - warnings
    - traceability
---

# Maximum Allowable Working Pressure (MAWP)

## Analysis purpose

Calculate the Maximum Allowable Working Pressure (MAWP) for straight pipe
sections when actual or ordered wall thickness and geometry are known.

## Required checks

- Material allowable stress at design temperature
- Pressure design thickness from actual thickness minus corrosion allowance
- MAWP from the thin-wall internal pressure equation per §304.1.2

## Dependency graph

```
Maximum Allowable Working Pressure (root)
|
+-- Table A-1 Allowable Stress (B313-table-A-1)
|
+-- MAWP Definition & Nomenclature (B313-MAWP-DEFINITION)
|   |
|   +-- Pressure Design Thickness (B313-MAWP-PRESSURE-DESIGN)
|   |
|   +-- MAWP Calculation §304.1.2 (B313-MAWP-CALCULATION)
```
