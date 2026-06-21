---
id: B313-PIPE-WALL-THICKNESS-DESIGN
type: root
title: Pipe Wall Thickness Design
version: "1.0"
status: draft
engineering_intent: pipe_wall_thickness_design

purpose: >
  Entry point for designing or verifying required pipe wall thickness under
  internal or external pressure per ASME B31.3 pressure design provisions.

depends_on:
  - node_id: B313-material-stress
    dependency_type: calculation
  - node_id: B313-304.1.1
    dependency_type: reference

report:
  template: pipe_wall_thickness_design
  include:
    - dependency_path
    - decisions
    - calculations
    - warnings
    - traceability
---

# Pipe Wall Thickness Design

## Analysis purpose

Verify or calculate the minimum required wall thickness for piping under internal or external pressure.

## Required checks

- Material allowable stress at design temperature
- Pressure loading case (internal or external)
- Required wall thickness under the governing pressure case

## Dependency graph

```
Pipe Wall Thickness Design (root)
|
+-- Material Stress (B313-material-stress)
|
+-- Required Thickness & Nomenclature §304.1.1 (B313-304.1.1)
|   |
|   +-- Internal Wall Thickness §304.1.2 (B313-304.1.2)  [when internal_pressure]
|   |
|   +-- External Wall Thickness §304.1.3 (B313-304.1.3)  [when external_pressure]
```
