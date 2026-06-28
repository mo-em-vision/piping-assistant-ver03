---
equation_id: mawp_pressure
name: Maximum Allowable Working Pressure
display: "MAWP = 2SEWt / (D - 2Yt)"
nomenclature_ref: B313-MAWP-DEFINITION

variables:
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
  t:
    symbol: t
    description: Pressure design thickness
    unit: mm
  D:
    symbol: D
    description: Outside diameter of pipe
    unit: mm
  Y:
    symbol: Y
    description: Coefficient from Table 304.1.1
    unit: dimensionless

steps:
  - name: compute_denominator
    description: Calculate D - 2Yt
    expressions:
      - expression: "D - 2 * Y * t"
        assign: denominator

  - name: compute_mawp
    description: Calculate Maximum Allowable Working Pressure
    expressions:
      - expression: "2 * S * E * W * t / denominator"
        assign: MAWP

outputs:
  - symbol: MAWP
    name: mawp
    unit: Pa
    type: quantity

executor: calculate_mawp
---

# Maximum Allowable Working Pressure

## Human-readable equation

```
MAWP = 2SEWt / (D - 2Yt)
```

Rearrangement of the thin-wall internal pressure equation per §304.1.2 when
pressure design thickness `t` is known.

Where symbols are defined in §304.1.1(b):

| Symbol | Meaning |
|--------|---------|
| `MAWP` | Maximum Allowable Working Pressure |
| `S` | Stress value from Table A-1 |
| `E` | Quality factor from Tables A-1A and A-1B |
| `W` | Weld strength reduction factor per para. 302.3.5(e) |
| `t` | Pressure design thickness |
| `D` | Outside diameter of pipe |
| `Y` | Coefficient from Table 304.1.1 |

## Execution notes

- Inputs must be in SI units (`Pa`, `mm`) at execution time.
- Result `MAWP` is in `Pa`.
