---
equation_id: eq-1b
name: Allowable Displacement Stress Range with Sustained Stress Margin
display: "S_A = f * (1.25*(S_c + S_h) - S_L)"
paragraph: "302.3.5(d)"
applies_when: "S_h > S_L and the difference is added to 0.25*S_h"

variables:
  f:
    symbol: f
    description: Stress range factor from eq. (1c)
    unit: dimensionless
  S_c:
    symbol: S_c
    description: Basic allowable stress at minimum metal temperature during displacement cycle analysis
    unit: Pa
  S_h:
    symbol: S_h
    description: Basic allowable stress at maximum metal temperature during displacement cycle analysis
    unit: Pa
  S_L:
    symbol: S_L
    description: Stress due to sustained loads
    unit: Pa

outputs:
  - symbol: S_A
    name: allowable_displacement_stress_range
    unit: Pa
    type: quantity

executor: calculate_allowable_displacement_stress_range_with_margin
calculation_module: eq_1b_allowable_displacement_stress_range_with_margin.py
---

# Eq. (1b) — Allowable Displacement Stress Range with Sustained Stress Margin

```
S_A = f * (1.25*(S_c + S_h) - S_L)
```

Use when `S_h > S_L` and the difference between them is added to the `0.25*S_h`
term in eq. (1a).
