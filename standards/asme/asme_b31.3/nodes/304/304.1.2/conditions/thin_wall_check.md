---
id: thin_wall_check
name: thin_wall_check
expression: "t < D/6"
description: >
  Determine whether the thin-wall pressure design equation in §304.1.2
  is applicable for the calculated thickness and outside diameter.

inputs:
  - symbol: t
    source: node_output
    description: Calculated pressure design thickness from wall_thickness equation
  - symbol: D
    source: user_input
    description: Outside diameter of pipe

result_if_true:
  decision: use_thin_wall_equation
  action: Continue with equations/wall_thickness.md result

result_if_false:
  decision: use_thick_wall_equation
  action: Route to thick-wall pressure design node (not yet implemented)

trace:
  capture:
    - expression
    - inputs
    - result
    - decision
---

# Thin-Wall Applicability Check

## Condition

```
t < D/6
```

## Engineering meaning

When the calculated pressure design thickness satisfies the thin-wall criterion, the pressure design equation referenced by §304.1.2 is applicable.

When the criterion is not satisfied, thick-wall provisions apply and this node's thin-wall equation result must not be used as the final design thickness without further evaluation.

## Evaluation order

1. Calculate provisional `t` using `equations/wall_thickness.md`.
2. Evaluate `t < D/6`.
3. Record the decision in the execution trace and report.
