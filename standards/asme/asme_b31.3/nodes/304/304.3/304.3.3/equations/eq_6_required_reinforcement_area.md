---
equation_id: eq-6
name: Required Reinforcement Area Under Internal Pressure
display: "A_1 = t_h d_1 (2 \\sin \\beta)"
nomenclature_ref: B313-304.3.3

variables:
  t_h:
    symbol: t_h
    description: Pressure design thickness of run pipe
    unit: mm
  d_1:
    symbol: d_1
    description: Effective length removed from pipe at branch
    unit: mm
  beta:
    symbol: β
    description: Smaller angle between axes of branch and run
    unit: deg

outputs:
  - symbol: A_1
    name: required_reinforcement_area
    unit: mm2
    type: quantity
---

# Required Reinforcement Area (eq. 6)

## Human-readable equation

```
$$
A_1 = t_h d_1 (2 \sin \beta)
\tag{6}
$$
```

For a branch connection under external pressure, area $A_1$ is one-half the area calculated by eq. (6), using as $t_h$ the thickness required for external pressure.

Symbols are defined in §304.3.3(a).
