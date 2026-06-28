---
equation_id: wall_thickness
name: Internal Pressure Wall Thickness
display: "t = PD / 2(SEW + PY)"
nomenclature_ref: B313-304.1.1

variables:
  P:
    symbol: P
    description: Internal design gage pressure
    unit: Pa
  D:
    symbol: D
    description: Outside diameter of pipe
    unit: mm
  S:
    symbol: S
    description: Stress value from Table A-1
    unit: Pa
  E:
    symbol: E
    description: Quality factor from Tables A-1A and A-1B
    unit: dimensionless
  W:
    symbol: W
    description: Weld strength reduction factor per para. 302.3.5(e)
    unit: dimensionless
  Y:
    symbol: Y
    description: Coefficient from Table 304.1.1
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
    description: Calculate pressure design wall thickness
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

Where symbols are defined in §304.1.1(b):

| Symbol | Meaning |
|--------|---------|
| `t` | Pressure design thickness |
| `P` | Internal design gage pressure |
| `D` | Outside diameter of pipe |
| `S` | Stress value from Table A-1 |
| `E` | Quality factor from Tables A-1A and A-1B |
| `W` | Weld strength reduction factor per para. 302.3.5(e) |
| `Y` | Coefficient from Table 304.1.1 |

## Execution notes

- Inputs must be in SI units (`Pa`, `mm`) at execution time.
- Result `t` is in `mm`.
- Intermediate values `SEW` and `PY` must be retained in the execution trace without rounding.
- Combine `t` with allowances `c` per §304.1.1 eq. (2) to obtain `t_m`.
