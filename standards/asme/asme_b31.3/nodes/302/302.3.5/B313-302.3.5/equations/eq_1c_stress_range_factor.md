---
equation_id: eq-1c
name: Stress Range Factor
display: "f = min(6.0*N^(-0.2), f_m)"
paragraph: "302.3.5(d)"

variables:
  N:
    symbol: N
    description: Equivalent number of full displacement cycles during expected service life
    unit: dimensionless
  f_m:
    symbol: f_m
    description: Maximum value of stress range factor
    unit: dimensionless

outputs:
  - symbol: f
    name: stress_range_factor
    unit: dimensionless
    type: quantity

executor: calculate_stress_range_factor
calculation_module: eq_1c_stress_range_factor.py
---

# Eq. (1c) — Stress Range Factor

```
f = min(6.0*N^(-0.2), f_m)
```

`f_m` is 1.2 for ferrous materials with specified minimum tensile strengths
≤ 517 MPa (75 ksi) at metal temperatures ≤ 371°C (700°F); otherwise `f_m = 1.0`.
