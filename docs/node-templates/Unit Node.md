# Unit Node Template

A Unit node defines a measurement unit and its deterministic conversion relationship to the canonical unit of its Dimension.

```yaml
---
id: UNIT-psi
type: unit

symbol: psi
name: Pound per Square Inch

dimension: DIM-pressure

description: >
  Pressure unit equal to one pound-force per square inch.

aliases:
  - PSI
  - lb/in2
  - lbf/in2

conversion:
  target: UNIT-Pa
  factor: 6894.757293168
  offset: 0

edges:
  - type: belongs_to_dimension
    target: DIM-pressure

  - type: converts_to
    target: UNIT-Pa
    factor: 6894.757293168
    offset: 0

metadata:
  status: active
  version: 1
---
```

## Required fields

|Field|Purpose|
|---|---|
|`id`|Stable unit identity. Must use `UNIT-*`.|
|`type`|Must be `unit`.|
|`symbol`|Display symbol.|
|`name`|Human-readable unit name.|
|`dimension`|The `DIM-*` node this unit belongs to.|
|`description`|Stable unit description.|

## Recommended fields

```yaml
aliases:
conversion:
metadata:
edges:
```

## Conversion rules

A Unit should convert to the canonical unit of its Dimension.

For linear conversions:

```yaml
conversion:
  target: UNIT-Pa
  factor: 100000
  offset: 0
```

For temperature conversions:

```yaml
conversion:
  target: UNIT-K
  factor: 1
  offset: 273.15
```

Example:

```yaml
---
id: UNIT-degC
type: unit

symbol: degC
name: Degree Celsius

dimension: DIM-temperature

description: >
  Celsius temperature scale.

aliases:
  - C
  - °C
  - celsius

conversion:
  target: UNIT-K
  factor: 1
  offset: 273.15

edges:
  - type: belongs_to_dimension
    target: DIM-temperature

  - type: converts_to
    target: UNIT-K
    factor: 1
    offset: 273.15

metadata:
  status: active
  version: 1
---
```

## Canonical unit example

```yaml
---
id: UNIT-Pa
type: unit

symbol: Pa
name: Pascal

dimension: DIM-pressure

description: >
  SI pressure unit equal to one newton per square meter.

aliases:
  - pascal

conversion:
  target: UNIT-Pa
  factor: 1
  offset: 0

edges:
  - type: belongs_to_dimension
    target: DIM-pressure

metadata:
  status: active
  version: 1
---
```

## Dimensionless unit example

```yaml
---
id: UNIT-dimensionless
type: unit

symbol: "1"
name: Dimensionless

dimension: DIM-dimensionless

description: >
  Unit used for ratios, factors, coefficients, and pure numbers.

aliases:
  - dimensionless
  - none
  - "-"

conversion:
  target: UNIT-dimensionless
  factor: 1
  offset: 0

edges:
  - type: belongs_to_dimension
    target: DIM-dimensionless

metadata:
  status: active
  version: 1
---
```

## Validation rules

A Unit node is invalid if:

1. `id` does not start with `UNIT-`.
    
2. `type` is not `unit`.
    
3. `symbol` is missing.
    
4. `dimension` does not reference a valid `DIM-*` node.
    
5. The unit is not allowed by its Dimension.
    
6. A non-canonical unit has no conversion rule.
    
7. Conversion creates a cycle that cannot resolve to the canonical unit.
    
8. The unit stores runtime values or project data.
    

## Forbidden fields

Unit nodes must not contain:

```yaml
value:
parameter:
fact:
source:
timestamp:
execution_id:
project_id:
workflow_id:
```

## Conceptual rule

```text
Dimension decides whether units are compatible.
Unit decides how values convert.
Parameter decides what the value means.
Fact stores the actual value.
```