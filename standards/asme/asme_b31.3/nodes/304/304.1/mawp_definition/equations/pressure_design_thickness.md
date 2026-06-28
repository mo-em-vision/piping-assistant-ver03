---
equation_id: pressure_design_thickness
name: Pressure Design Thickness from Actual Thickness
display: "t = t_actual - c"
nomenclature_ref: B313-MAWP-DEFINITION

variables:
  t_actual:
    symbol: t_actual
    description: Actual or ordered wall thickness
    unit: mm
  c:
    symbol: c
    description: Corrosion allowance
    unit: mm

steps:
  - name: compute_pressure_design_thickness
    description: Subtract corrosion allowance from actual thickness
    expressions:
      - expression: "t_actual - c"
        assign: t

outputs:
  - symbol: t
    name: pressure_design_thickness
    unit: mm
    type: quantity

executor: calculate_pressure_design_thickness
---

# Pressure Design Thickness

## Human-readable equation

```
t = t_actual - c
```

Where:

| Symbol | Meaning |
|--------|---------|
| `t` | Pressure design thickness |
| `t_actual` | Actual or ordered wall thickness |
| `c` | Corrosion allowance |

## Execution notes

- Inputs must be in SI units (`mm`) at execution time.
- Result `t` is in `mm`.
