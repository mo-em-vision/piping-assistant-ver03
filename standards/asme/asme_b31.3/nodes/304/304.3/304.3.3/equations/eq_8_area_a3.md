---
equation_id: eq-8
name: Branch Pipe Excess Thickness Area
display: "A_3 = 2L_4(T_b - t_b - c)/\\sin(\\beta)"
nomenclature_ref: B313-304.3.3

variables:
  L_4:
    symbol: L_4
    description: Height of reinforcement zone outside run pipe
    unit: mm
  T_b:
    symbol: T_b
    description: Branch pipe wall thickness
    unit: mm
  t_b:
    symbol: t_b
    description: Pressure design thickness of branch pipe
    unit: mm
  c:
    symbol: c
    description: Corrosion allowance
    unit: mm
  beta:
    symbol: β
    description: Smaller angle between axes of branch and run
    unit: deg

outputs:
  - symbol: A_3
    name: branch_excess_thickness_area
    unit: mm2
    type: quantity
---

# Area A_3 (eq. 8)

## Human-readable equation

```
$$
A_3 = 2L_4(T_b - t_b - c)/\sin(\beta)
\tag{8}
$$
```

If the allowable stress for the branch pipe wall is less than that for the run pipe, its calculated area shall be reduced in the ratio of allowable stress values of the branch to the run in determining its contribution to area $A_3$.
