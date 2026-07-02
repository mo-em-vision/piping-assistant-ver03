# Dimension Node Template

A Dimension node defines a measurable or semantic category used to determine unit compatibility for Parameters and Facts.

```yaml
---
id: DIM-pressure
type: dimension

key: pressure
name: Pressure

dimension_kind: physical
canonical_unit: UNIT-Pa

description: >
  Force per unit area. Stress quantities share this dimension.

aliases:
  - stress

edges:
  - type: allows_unit
    target: UNIT-Pa

  - type: allows_unit
    target: UNIT-MPa

  - type: allows_unit
    target: UNIT-psi

  - type: allows_unit
    target: UNIT-bar

metadata:
  status: active
  version: 1
---
```

## Required fields

|Field|Purpose|
|---|---|
|`id`|Stable dimension identity. Must use `DIM-*`.|
|`type`|Must be `dimension`.|
|`key`|Machine-safe semantic key.|
|`name`|Human-readable dimension name.|
|`dimension_kind`|`physical`, `dimensionless`, or `categorical`.|
|`description`|Stable definition.|

## Required for physical dimensions

```yaml
canonical_unit: UNIT-*
edges:
  - type: allows_unit
    target: UNIT-*
```

## Recommended edge type

Prefer:

```yaml
type: allows_unit
```

instead of:

```yaml
type: references
```

because the relationship is more specific.

## Example: length

```yaml
---
id: DIM-length
type: dimension

key: length
name: Length

dimension_kind: physical
canonical_unit: UNIT-mm

description: >
  Linear distance, thickness, diameter, and other length measures.

edges:
  - type: allows_unit
    target: UNIT-m

  - type: allows_unit
    target: UNIT-mm

  - type: allows_unit
    target: UNIT-in

metadata:
  status: active
  version: 1
---
```

## Example: dimensionless

```yaml
---
id: DIM-dimensionless
type: dimension

key: dimensionless
name: Dimensionless

dimension_kind: dimensionless
canonical_unit: UNIT-dimensionless

description: >
  Ratios, counts, coefficients, factors, and other quantities without physical units.

edges:
  - type: allows_unit
    target: UNIT-dimensionless

metadata:
  status: active
  version: 1
---
```

## Example: material designation

```yaml
---
id: DIM-material-designation
type: dimension

key: material_designation
name: Material Designation

dimension_kind: categorical
canonical_unit: null

description: >
  Material specification, grade, or designation used to resolve properties,
  limits, allowable stresses, and material-dependent engineering rules.

edges: []

metadata:
  status: active
  version: 1
---
```

## Validation rules

A Dimension node is invalid if:

1. `id` does not start with `DIM-`.
    
2. `type` is not `dimension`.
    
3. `key` is missing or not unique.
    
4. `dimension_kind` is missing.
    
5. `dimension_kind: physical` has no `canonical_unit`.
    
6. `dimension_kind: physical` has no allowed unit edges.
    
7. `canonical_unit` is not included in the allowed unit edges.
    
8. `dimension_kind: categorical` defines a real unit conversion.
    
9. A dimension stores values, runtime facts, project data, or execution state.
    

## Forbidden fields

Dimension nodes must not contain:

```yaml
value:
unit_value:
source:
timestamp:
execution_id:
workflow_id:
project_id:
resolution:
```

## Conceptual rule

```text
Dimension defines compatibility.
Unit defines conversion.
Parameter references Dimension.
Fact stores values using allowed Units.
```