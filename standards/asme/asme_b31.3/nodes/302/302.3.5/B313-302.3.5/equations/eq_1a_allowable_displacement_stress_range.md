---
equation_id: eq-1a
name: Allowable Displacement Stress Range
display: "S_A = f * (1.25*S_c + 0.25*S_h)"
paragraph: "302.3.5(d)"
applies_when: standard allowable displacement stress range calculation

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

outputs:
  - symbol: S_A
    name: allowable_displacement_stress_range
    unit: Pa
    type: quantity

executor: calculate_allowable_displacement_stress_range
calculation_module: eq_1a_allowable_displacement_stress_range.py
---

# Eq. (1a) — Allowable Displacement Stress Range

```
S_A = f * (1.25*S_c + 0.25*S_h)
```

Use when the standard displacement stress range limit applies without adding the
`S_h - S_L` margin to the `0.25*S_h` term.
