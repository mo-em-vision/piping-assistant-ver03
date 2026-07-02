# Parameter Node Template

A Parameter node defines a reusable engineering concept. It does **not** store values, user inputs, runtime state, or execution resolution strategy.

```yaml
---
id: PARAM-design-pressure
type: parameter

key: design_pressure
name: Design Pressure

parameter_class: physical_quantity
dimension: DIM-pressure

description: >
  Pressure used as the basis for engineering design calculations.

canonical_symbol: P

aliases:
  - design pressure
  - internal design pressure

introduced_by:
  - B313-304.1.2

edges:
  - type: has_dimension
    target: DIM-pressure

  - type: introduced_by
    target: B313-304.1.2

  - type: used_by
    target: EQ-B313-wall-thickness

metadata:
  status: active
  version: 1
---
```

## Required fields

|Field|Purpose|
|---|---|
|`id`|Stable canonical parameter identity. Prefer `PARAM-*`, not standard-owned IDs.|
|`type`|Must be `parameter`.|
|`key`|Machine-safe semantic key.|
|`name`|Human-readable canonical name.|
|`parameter_class`|Kind of parameter.|
|`dimension`|Reference to a `DIM-*` node.|
|`description`|Stable semantic definition.|

## Recommended `parameter_class` values

```yaml
physical_quantity
geometric_quantity
material_designation
coefficient
factor
categorical
environmental_condition
calculated_quantity
selection
```

## Dimension examples

```yaml
dimension: DIM-pressure
dimension: DIM-length
dimension: DIM-temperature
dimension: DIM-dimensionless
dimension: DIM-material-designation
```

## Important rules

Parameter nodes must not contain:

```yaml
value:
unit:
resolution:
source:
timestamp:
execution_id:
workflow_id:
status:
```

Those belong to **Facts**, **Execution Context**, or **Workflow/Planner logic**.

## Example: material parameter

```yaml
---
id: PARAM-material-specification
type: parameter

key: material_specification
name: Material Specification

parameter_class: material_designation
dimension: DIM-material-designation

description: >
  Material specification or designation used to resolve allowable stress,
  material properties, and applicable standard limits.

canonical_symbol: material

aliases:
  - pipe material
  - material
  - material grade

introduced_by:
  - B313-304.1.1
  - B313-302.3.5

edges:
  - type: has_dimension
    target: DIM-material-designation

  - type: introduced_by
    target: B313-304.1.1

  - type: used_by
    target: LOOKUP-B313-material-allowable-stress

metadata:
  status: active
  version: 1
---
```

## Example: corrosion allowance parameter

```yaml
---
id: PARAM-corrosion-allowance
type: parameter

key: corrosion_allowance
name: Corrosion Allowance

parameter_class: geometric_quantity
dimension: DIM-length

description: >
  Additional wall thickness allowance provided to account for expected
  corrosion, erosion, or mechanical allowance over the service life.

canonical_symbol: c

aliases:
  - corrosion allowance
  - mechanical allowance
  - allowance

introduced_by:
  - B313-304.1.1

edges:
  - type: has_dimension
    target: DIM-length

  - type: introduced_by
    target: B313-304.1.1

  - type: used_by
    target: EQ-B313-minimum-required-thickness

metadata:
  status: active
  version: 1
---
```

## Conceptual rule

```text
Parameter defines the concept.
Dimension defines compatible units.
Unit defines conversion.
Fact stores actual value.
Workflow/Planner decides how the Fact is obtained.
```