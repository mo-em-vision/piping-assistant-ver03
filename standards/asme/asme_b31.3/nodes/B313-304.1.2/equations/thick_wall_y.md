---
id: thick_wall_y
title: Thick-Wall Temperature Coefficient Y
equation: "Y = (d + 2c) / (D + d + 2c)"
symbols:
  - symbol: Y
    description: Temperature coefficient for thick-wall pipe (t >= D/6)
  - symbol: d
    description: Inside diameter per §304.1.1(b)
  - symbol: D
    description: Outside diameter
  - symbol: c
    description: Sum of mechanical, corrosion, and erosion allowances
---

# Thick-Wall Coefficient Y

When **t ≥ D/6**, the coefficient **Y** is computed per §304.1.1(b):

```
Y = (d + 2c) / (D + d + 2c)
```

Where **d** is the inside diameter (maximum value allowable under the purchase specification).
