---
formula_id: wall_thickness
name: Internal Pressure Wall Thickness
display: "t = PD / 2(SEW + PY)"

variables:
  P:
    symbol: P
    description: Internal design pressure
    unit: Pa
  D:
    symbol: D
    description: Outside diameter
    unit: mm
  S:
    symbol: S
    description: Allowable stress at design temperature
    unit: Pa
  E:
    symbol: E
    description: Weld joint quality factor
    unit: dimensionless
  W:
    symbol: W
    description: Weld strength reduction factor
    unit: dimensionless
  Y:
    symbol: Y
    description: Temperature coefficient
    unit: dimensionless

steps:
  - name: compute_denominator_terms
    description: Calculate SEW and PY terms
    expressions:
      - expression: "S * E * W"
        assign: SEW
      - expression: "P * Y"
        assign: PY

  - name: compute_required_thickness
    description: Calculate minimum required wall thickness
    expressions:
      - expression: "P * D / (2 * (SEW + PY))"
        assign: t

outputs:
  - symbol: t
    name: required_thickness
    unit: mm
    type: quantity

executor: calculate_wall_thickness
---

# Internal Pressure Wall Thickness

## Human-readable equation

```
t = PD / 2(SEW + PY)
```

Where:

| Symbol | Meaning |
|--------|---------|
| `t` | Required wall thickness |
| `P` | Internal design pressure |
| `D` | Outside diameter |
| `S` | Allowable stress at design temperature |
| `E` | Weld joint quality factor |
| `W` | Weld strength reduction factor |
| `Y` | Temperature coefficient |

## Execution notes

- Inputs must be in SI units (`Pa`, `mm`) at execution time.
- Result `t` is in `mm`.
- Intermediate values `SEW` and `PY` must be retained in the execution trace without rounding.
