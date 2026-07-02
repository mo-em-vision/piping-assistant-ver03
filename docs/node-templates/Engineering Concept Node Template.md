# Engineering Concept Node Template

An Engineering Concept node defines a reusable semantic engineering idea.

A Concept is broader than a Parameter.  
A Parameter is a contextual role of a Concept.

```yaml
---
id: CONCEPT-pressure
type: concept

key: pressure
name: Pressure

concept_class: physical_quantity
dimension: DIM-pressure

description: >
  The engineering concept of pressure as force per unit area. This concept
  includes design pressure, operating pressure, test pressure, allowable
  pressure, and other pressure-related parameters.

aliases:
  - stress pressure
  - internal pressure
  - external pressure

edges:
  - type: has_dimension
    target: DIM-pressure

  - type: specializes
    target: CONCEPT-physical-quantity

  - type: has_parameter
    target: PARAM-design-pressure

  - type: has_parameter
    target: PARAM-operating-pressure

  - type: has_parameter
    target: PARAM-hydrotest-pressure

metadata:
  status: active
  version: 1
---
```

## Purpose

Engineering Concepts exist to prevent Parameters from becoming isolated labels.

They allow the graph to understand that several Parameters may belong to the same underlying engineering idea.

Example:

```text
CONCEPT-pressure
  ├── PARAM-design-pressure
  ├── PARAM-operating-pressure
  ├── PARAM-hydrotest-pressure
  └── PARAM-maximum-allowable-working-pressure
```

The Parameters are different engineering roles, but they all belong to the same Concept.

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Stable concept identity. Must use `CONCEPT-*`.|
|`type`|Must be `concept`.|
|`key`|Machine-safe semantic key.|
|`name`|Human-readable concept name.|
|`concept_class`|Type of engineering concept.|
|`description`|Stable semantic definition.|

---

# Recommended `concept_class` values

```yaml
physical_quantity
geometric_quantity
material
fluid
component
condition
coefficient
factor
selection
category
failure_mode
inspection_method
authority_concept
```

---

# Physical concept example

```yaml
---
id: CONCEPT-wall-thickness
type: concept

key: wall_thickness
name: Wall Thickness

concept_class: geometric_quantity
dimension: DIM-length

description: >
  The engineering concept of pipe, vessel, or component wall thickness.
  This concept includes nominal, measured, required, minimum, ordered,
  and corroded wall thickness parameters.

aliases:
  - thickness
  - pipe wall thickness
  - component thickness

edges:
  - type: has_dimension
    target: DIM-length

  - type: has_parameter
    target: PARAM-required-wall-thickness

  - type: has_parameter
    target: PARAM-measured-wall-thickness

  - type: has_parameter
    target: PARAM-nominal-wall-thickness

  - type: has_parameter
    target: PARAM-ordered-wall-thickness

metadata:
  status: active
  version: 1
---
```

---

# Categorical concept example

```yaml
---
id: CONCEPT-material
type: concept

key: material
name: Material

concept_class: material
dimension: null

description: >
  The engineering concept of material identity, including specification,
  grade, product form, and material family.

aliases:
  - engineering material
  - construction material

edges:
  - type: has_parameter
    target: PARAM-material-specification

  - type: has_parameter
    target: PARAM-material-grade

  - type: has_parameter
    target: PARAM-pipe-material

  - type: has_parameter
    target: PARAM-bolt-material

metadata:
  status: active
  version: 1
---
```

---

# Selection concept example

```yaml
---
id: CONCEPT-joint-category
type: concept

key: joint_category
name: Joint Category

concept_class: selection
dimension: null

description: >
  The engineering concept used to classify joint construction, weld type,
  or joint quality category for resolving quality factors or fabrication
  rules.

aliases:
  - weld category
  - joint type
  - weld joint category

edges:
  - type: has_parameter
    target: PARAM-joint-category

  - type: used_by
    target: LOOKUP-B313-quality-factor

metadata:
  status: active
  version: 1
---
```

---

# Relationship rules

Concepts may connect to:

```yaml
has_dimension
has_parameter
specializes
generalizes
related_to
used_by
introduced_by
constrained_by
```

Recommended examples:

```yaml
edges:
  - type: has_dimension
    target: DIM-pressure

  - type: has_parameter
    target: PARAM-design-pressure

  - type: introduced_by
    target: B313-304.1.2

  - type: constrained_by
    target: B313-302.2.4

  - type: used_by
    target: EQ-B313-wall-thickness
```

---

# Concept vs Dimension vs Parameter

## Dimension

Defines unit compatibility.

Example:

```yaml
DIM-length
```

Meaning:

```text
Can this value be expressed in mm, m, or in?
```

---

## Concept

Defines semantic engineering meaning.

Example:

```yaml
CONCEPT-wall-thickness
```

Meaning:

```text
This is about the physical idea of wall thickness.
```

---

## Parameter

Defines contextual engineering role.

Example:

```yaml
PARAM-required-wall-thickness
PARAM-measured-wall-thickness
PARAM-nominal-wall-thickness
```

Meaning:

```text
Which kind of wall thickness is being used in this engineering situation?
```

---

# Validation rules

A Concept node is invalid if:

1. `id` does not start with `CONCEPT-`.
    
2. `type` is not `concept`.
    
3. `key` is missing or not unique.
    
4. `concept_class` is missing.
    
5. A physical or geometric concept does not reference a valid Dimension.
    
6. A categorical concept references a physical Dimension without justification.
    
7. It stores runtime values.
    
8. It duplicates another Concept with the same semantic meaning.
    
9. It defines execution logic directly.
    
10. It replaces a Parameter where contextual role is required.
    

---

# Forbidden fields

Concept nodes must not contain:

```yaml
value:
unit:
source:
timestamp:
execution_id:
workflow_id:
project_id:
resolution:
formula:
calculation_result:
```

---

# Conceptual rule

```text
Concept defines semantic meaning.
Dimension defines unit compatibility.
Parameter defines contextual role.
Fact stores runtime value.
```

---

# Recommended placement

Concept nodes should live in a shared ontology layer, not inside a single standard pack.

Example:

```text
ontology/
  concepts/
    CONCEPT-pressure/
      node.yaml
    CONCEPT-wall-thickness/
      node.yaml
    CONCEPT-material/
      node.yaml

  dimensions/
    DIM-pressure/
      node.yaml

  units/
    UNIT-Pa/
      node.yaml
```

Standards should reference Concepts.  
Standards should not own Concepts.

---

# Example hierarchy

```text
CONCEPT-pressure
  ├── DIM-pressure
  ├── PARAM-design-pressure
  ├── PARAM-operating-pressure
  ├── PARAM-hydrotest-pressure
  └── PARAM-allowable-pressure

CONCEPT-wall-thickness
  ├── DIM-length
  ├── PARAM-required-wall-thickness
  ├── PARAM-nominal-wall-thickness
  ├── PARAM-measured-wall-thickness
  └── PARAM-corrosion-allowance

CONCEPT-material
  ├── PARAM-material-specification
  ├── PARAM-material-grade
  ├── PARAM-pipe-material
  └── PARAM-bolt-material
```