# Parameter Node Template

A Parameter node defines a reusable engineering concept. It does **not** store values, user inputs, runtime state, or execution resolution strategy.

Do **not** author a top-level `links` metadata block — object relationships belong in typed `edges` only ([`_relationship_schema.md`](_relationship_schema.md#on-disk-rule)). **Exception:** declare where a parameter is introduced in the top-level `introduced_by` list (not in `edges`); the graph compiler emits `introduced_by` edges at build time.

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
  - asme-b313-304-1-1-b

edges:
  - type: has_dimension
    target: DIM-pressure

  - type: used_by
    target: asme-b313-304-1-2-eq-3a

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
|`introduced_by`|Pack-qualified paragraph id(s) where the symbol is introduced (top-level list only; not `edges`).|

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

### `selection` and `categorical` control runtime behavior

These `parameter_class` values drive planner prompts, UI input type, and lookup gating. They do **not** belong on Concept nodes — Concepts only group semantic meaning. See [Engineering Concept](Engineering%20Concept.md#selection-vs-categorical-where-each-belongs).

- **`selection`**: discrete workflow choice (dropdown/confirmation); e.g. joint category before E lookup.
- **`categorical`**: label-based designation stored as a Fact `{label, normalized_key}`; e.g. material specification token.

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

## Cross-pack paragraph traceability

Global `PARAM-*` nodes live outside any standards pack. When a parameter is introduced or used by a **paragraph**, reference the paragraph with a **pack-qualified id** so multiple standards do not collide:

| Pack | Prefix | Bare paragraph `id` | Qualified reference |
| --- | --- | --- | --- |
| ASME B31.3 | `asme-b313` | `304.1.1-b` | `asme-b313-304-1-1-b` |
| ASME B31.3 | `asme-b313` | `302.3.5-e` | `asme-b313-302-3-5-e` |

Use pack-qualified ids in the top-level `introduced_by` list only — do **not** duplicate them as `introduced_by` edges. Paragraph nodes inside a pack keep their bare `id` (`304.1.1-b`); the graph compiler resolves qualified references at compile time. Helpers: [`engine/reference/asme_b313_node_ids.py`](../../engine/reference/asme_b313_node_ids.py).

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
  - asme-b313-304-1-1-b

edges:
  - type: has_dimension
    target: DIM-material-designation

  - type: used_by
    target: asme-b313-table-A-1

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
  - asme-b313-304-1-1-b

edges:
  - type: has_dimension
    target: DIM-length

  - type: used_by
    target: asme-b313-304-1-1-eq-2

metadata:
  status: active
  version: 1
---
```

## Example: joint category parameter

```yaml
---
id: PARAM-joint-category
type: parameter

key: joint_category
name: Joint Category

parameter_class: selection

description: >
  Pipe or joint construction category used to resolve weld joint quality
  factor E from Tables A-2 and A-3.

canonical_symbol: joint_category

aliases:
  - weld category
  - joint type
  - weld joint category

introduced_by:
  - asme-b313-304-1-2-a

edges:
  - type: used_by
    target: asme-b313-table-A-3

metadata:
  status: active
  version: 1
---
```

Semantic grouping lives on [`CONCEPT-joint-category`](../../knowledge/global/concepts/nodes/CONCEPT-joint-category.yaml); this Parameter owns the contextual role and selection behavior.

## Conceptual rule

```text
Concept defines semantic meaning.
Parameter defines contextual role and behavior class.
Dimension defines compatible units.
Unit defines conversion.
Fact stores actual value.
Workflow/Planner decides how the Fact is obtained.
```