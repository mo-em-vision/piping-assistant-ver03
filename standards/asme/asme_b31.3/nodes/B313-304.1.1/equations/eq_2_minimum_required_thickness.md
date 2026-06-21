---
equation_id: eq-2
name: Minimum Required Thickness
display: "t_m = t + c"
nomenclature_ref: B313-304.1.1

variables:
  t:
    symbol: t
    description: Pressure design thickness from §304.1.2 or §304.1.3
    unit: mm
  c:
    symbol: c
    description: Sum of mechanical, corrosion, and erosion allowances
    unit: mm

steps:
  - name: compute_minimum_required_thickness
    description: Combine pressure design thickness with corrosion allowance
    expressions:
      - expression: "t + c"
        assign: t_m

outputs:
  - symbol: t_m
    name: minimum_required_thickness
    unit: mm
    type: quantity

executor: calculate_minimum_required_thickness
---

# Minimum Required Thickness (eq. 2)

## Human-readable equation

```
t_m = t + c
```

Where symbols are defined in §304.1.1(b):

| Symbol | Meaning |
|--------|---------|
| `t_m` | Minimum required thickness |
| `t` | Pressure design thickness |
| `c` | Corrosion and erosion allowances |

## Execution notes

- Inputs must be in SI units (`mm`) at execution time.
- Result `t_m` is in `mm`.
- Selected pipe wall thickness **T** must be not less than `t_m` per §304.1.1(a).
