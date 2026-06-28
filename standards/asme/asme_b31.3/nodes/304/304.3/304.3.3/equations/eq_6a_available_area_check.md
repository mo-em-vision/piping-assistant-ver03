---
equation_id: eq-6a
name: Available Reinforcement Area Check
display: "A_2 + A_3 + A_4 \\ge A_1"
nomenclature_ref: B313-304.3.3

variables:
  A_2:
    symbol: A_2
    description: Area from excess thickness in run pipe wall
    unit: mm2
  A_3:
    symbol: A_3
    description: Area from excess thickness in branch pipe wall
    unit: mm2
  A_4:
    symbol: A_4
    description: Area from welds and attached reinforcement
    unit: mm2
  A_1:
    symbol: A_1
    description: Required reinforcement area
    unit: mm2

outputs:
  - symbol: reinforcement_adequate
    name: reinforcement_adequate
    unit: dimensionless
    type: boolean
---

# Available Reinforcement Area (eq. 6a)

## Human-readable equation

```
$$
A_2 + A_3 + A_4 \ge A_1
\tag{6a}
$$
```

These areas are all within the reinforcement zone and are further defined in §304.3.3(c).
