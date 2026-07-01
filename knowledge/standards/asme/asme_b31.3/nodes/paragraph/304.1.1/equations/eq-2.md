---
id: 304.1.1-eq-2
type: equation
equation_id: eq-2
name: Minimum Required Pipe Wall Thickness
display: t_m = t + c
nomenclature_ref: 304.1.1
status: superseded
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
  - expression: t + c
    assign: t_m
executor: calculate_minimum_required_thickness
edges:
- type: parent
  target: 304.1.1
---

# Minimum Required Thickness (eq. 2)

## Human-readable equation

```
t_m = t + c
```

Where symbols are defined in §304.1.1(b):

| Symbol | Meaning |
| ------ | ------- |
| `t_m`  | minimum required thickness, including mechanical, corrosion, and erosion allowances |
| `t`    | pressure design thickness, as calculated in accordance with [para. 304.1.2](node:304.1.2) for internal pressure or as determined in accordance with [para. 304.1.3](node:304.1.3) for external pressure |
| `c`    | sum of the mechanical allowances (thread or groove depth) plus corrosion and erosion allowances. For threaded components, the nominal thread depth (dimension h of ASME B1.20.1, or equivalent) shall apply. For machined surfaces or grooves where the tolerance is not specified, the tolerance shall be assumed to be 0.5 mm (0.02 in.) in addition to the specified depth of the cut. |

## Execution notes

- Inputs must be in SI units (`mm`) at execution time.
- Result `t_m` is in `mm`.
- Selected pipe wall thickness **T** must be not less than `t_m` per §304.1.1(a).
