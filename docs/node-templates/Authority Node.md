# Authority Node Template

> **Implementation:** [`knowledge/global/authorities/nodes/AUTH-*.yaml`](../../knowledge/global/authorities/nodes/); canonical type `authority` in [`engine/reference/node_types.py`](../../engine/reference/node_types.py). Runtime selection via [`Authority Context`](Authority%20Context.md) (`active_authorities[].authority_id`).

An Authority node defines a canonical authoritative engineering source.

Examples include standards, codes, regulations, company specifications, project specifications, material standards, recommended practices, and approved engineering procedures.

An Authority node is part of the immutable authority graph.  
It does not store runtime values.  
It does not decide whether it is active for a specific execution.  
Authority Context decides that.

```yaml
---
id: AUTH-ASME-B31.3
type: authority

key: asme_b31_3
name: ASME B31.3

authority_class: design_code
publisher: ASME

title: Process Piping

description: >
  ASME B31.3 Process Piping code used for design, construction,
  examination, inspection, and testing of process piping systems.

editions:
  - year: 2024
    status: active
    effective_date: null

  - year: 2022
    status: superseded

scope:
  domain:
    - piping

  equipment:
    - process_piping

  lifecycle_phase:
    - design
    - construction
    - examination
    - testing

contains:
  paragraphs:
    - B313-304.1.1
    - B313-304.1.2
    - B313-302.3.5

  tables:
    - TABLE-B313-allowable-stress
    - TABLE-B313-Y-coefficient

edges:
  - type: contains_paragraph
    target: B313-304.1.1

  - type: contains_paragraph
    target: B313-304.1.2

  - type: contains_table
    target: TABLE-B313-allowable-stress

metadata:
  status: active
  version: 1
---
```

---

# Purpose

An Authority node answers:

```text
What authoritative source does this engineering knowledge come from?
```

Examples:

```text
ASME B31.3
ASME B36.10M
ASTM A106
API 570
API 650
Company Piping Specification
Project Design Basis
Local Regulation
Client Requirement
```

Authority nodes are not runtime selections.  
They define sources that may later be activated by an Authority Context.

---

# Authority vs Authority Context

```text
Authority Node
  Defines the source.

Authority Context
  Selects the source for a specific execution.
```

Example:

```text
AUTH-ASME-B31.3
  = the canonical ASME B31.3 authority source

AUTHCTX-001
  = ASME B31.3 2024 is active for this pipe wall thickness task
```

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Stable authority identity. Must use `AUTH-*`.|
|`type`|Must be `authority`.|
|`key`|Machine-safe authority key.|
|`name`|Human-readable authority name.|
|`authority_class`|Type of authority source.|
|`description`|Stable description of the authority.|
|`metadata`|Status and implementation version.|

---

# Recommended fields

|Field|Purpose|
|---|---|
|`publisher`|Organization or owner of the authority.|
|`title`|Formal title.|
|`editions`|Known editions or revisions.|
|`scope`|Domain and applicability.|
|`contains`|Paragraphs, tables, figures, or rules belonging to the authority.|
|`edges`|Explicit graph relationships.|

---

# Recommended `authority_class` values

```yaml
design_code
inspection_code
material_standard
dimensional_standard
testing_standard
regulation
company_standard
project_specification
client_requirement
recommended_practice
engineering_procedure
manufacturer_document
```

---

# Examples

## ASME B31.3

```yaml
---
id: AUTH-ASME-B31.3
type: authority

key: asme_b31_3
name: ASME B31.3

authority_class: design_code
publisher: ASME
title: Process Piping

description: >
  Design code for process piping systems.

scope:
  domain:
    - piping
  lifecycle_phase:
    - design
    - construction
    - examination
    - testing

editions:
  - year: 2024
    status: active

contains:
  paragraphs:
    - B313-304.1.1
    - B313-304.1.2
    - B313-302.3.5

  tables:
    - TABLE-B313-allowable-stress

edges:
  - type: contains_paragraph
    target: B313-304.1.1

  - type: contains_table
    target: TABLE-B313-allowable-stress

metadata:
  status: active
  version: 1
---
```

---

## ASTM A106

```yaml
---
id: AUTH-ASTM-A106
type: authority

key: astm_a106
name: ASTM A106

authority_class: material_standard
publisher: ASTM

title: Seamless Carbon Steel Pipe for High-Temperature Service

description: >
  Material standard defining requirements for seamless carbon steel pipe
  intended for high-temperature service.

scope:
  domain:
    - materials
    - piping

  material_family:
    - carbon_steel

  product_form:
    - seamless_pipe

contains:
  material_designations:
    - ASTM A106 Grade A
    - ASTM A106 Grade B
    - ASTM A106 Grade C

  tables:
    - TABLE-ASTM-A106-mechanical-properties
    - TABLE-ASTM-A106-chemical-composition

edges:
  - type: defines_material_specification
    target: PARAM-material-specification

  - type: contains_table
    target: TABLE-ASTM-A106-mechanical-properties

  - type: contains_table
    target: TABLE-ASTM-A106-chemical-composition

metadata:
  status: active
  version: 1
---
```

---

## ASME B36.10M

```yaml
---
id: AUTH-ASME-B36.10M
type: authority

key: asme_b36_10m
name: ASME B36.10M

authority_class: dimensional_standard
publisher: ASME

title: Welded and Seamless Wrought Steel Pipe

description: >
  Dimensional standard defining sizes, outside diameters, wall thicknesses,
  and schedules for welded and seamless wrought steel pipe.

scope:
  domain:
    - piping

  concept:
    - CONCEPT-pipe-dimensions

contains:
  tables:
    - TABLE-B36.10M-pipe-dimensions

edges:
  - type: contains_table
    target: TABLE-B36.10M-pipe-dimensions

  - type: defines_parameter_values_for
    target: PARAM-outside-diameter

  - type: defines_parameter_values_for
    target: PARAM-nominal-wall-thickness

metadata:
  status: active
  version: 1
---
```

---

## Company piping specification

```yaml
---
id: AUTH-COMPANY-PIPING-SPEC
type: authority

key: company_piping_spec
name: Company Piping Specification

authority_class: company_standard
publisher: Internal

title: Refinery Piping Design Specification

description: >
  Internal company piping design requirements that refine or supplement
  applicable design codes and project requirements.

scope:
  domain:
    - piping

  lifecycle_phase:
    - design
    - operation
    - maintenance

authority_behavior:
  refines:
    - AUTH-ASME-B31.3

  may_override:
    - AUTH-ASME-B31.3

  precedence_default: above_design_code

edges:
  - type: refines_authority
    target: AUTH-ASME-B31.3

  - type: constrains_parameter
    target: PARAM-corrosion-allowance

  - type: constrains_workflow
    target: WF-pipe-wall-thickness-design

metadata:
  status: active
  version: 1
---
```

---

# Scope model

The `scope` field defines where the Authority is generally applicable.

```yaml
scope:
  domain:
    - piping

  equipment:
    - process_piping

  lifecycle_phase:
    - design
    - construction
    - testing

  material_family:
    - carbon_steel
```

Scope does not automatically activate the Authority.  
It only helps the Planner or Authority Resolver determine candidates.

Authority Context activates the Authority for execution.

---

# Edition model

Authorities may have multiple editions.

```yaml
editions:
  - year: 2024
    status: active
    effective_date: null

  - year: 2022
    status: superseded
```

The Authority node can list available editions, but the active edition for a task belongs to Authority Context.

Example:

```yaml
active_authorities:
  - authority_id: AUTH-ASME-B31.3
    edition: 2024
```

---

# Authority contents

Authority nodes may contain or reference:

```yaml
contains:
  paragraphs:
    - B313-304.1.2

  tables:
    - TABLE-B313-allowable-stress

  figures:
    - FIG-B313-example

  rules:
    - RULE-B313-thin-wall-limit
```

The actual Paragraph, Table, Rule, or Figure nodes remain separate nodes.

Authority does not duplicate their content.

---

# Allowed relationships

Authority nodes may use these relationships in template prose. **On-disk YAML** uses native taxonomy types from [`_relationship_schema.md`](_relationship_schema.md):

| Template edge | Stored YAML edge |
|---------------|------------------|
| `contains_paragraph` | `type: contains_paragraph` |
| `contains_table` | `type: contains_table` |
| `refines_authority` | `type: refines_authority` |
| `constrains_parameter` | `type: constrains_parameter` |

Authority nodes may connect to:

```yaml
contains_paragraph
contains_table
contains_figure
contains_rule
defines_material_specification
defines_requirement
defines_acceptance_criteria
defines_parameter_values_for
constrains_parameter
constrains_workflow
refines_authority
supersedes_authority
conflicts_with_authority
references_authority
```

Example:

```yaml
edges:
  - type: contains_paragraph
    target: B313-304.1.2

  - type: contains_table
    target: TABLE-B313-allowable-stress

  - type: refines_authority
    target: AUTH-ASME-B31.3

  - type: constrains_parameter
    target: PARAM-corrosion-allowance
```

---

# Authority hierarchy

Do not hard-code universal precedence into Authority nodes.

Precedence is usually project-specific.

For example, a company specification may override ASME B31.3 in one company, but not in another project.

Therefore:

```text
Authority node:
  May describe general relationship.

Authority Context:
  Defines active hierarchy for this execution.
```

Good in Authority node:

```yaml
authority_behavior:
  refines:
    - AUTH-ASME-B31.3
```

Good in Authority Context:

```yaml
authority_hierarchy:
  - level: 2
    authority_type: company_standard

  - level: 4
    authority_type: design_code
```

---

# Relationship to Concepts and Parameters

Authority does not own engineering concepts.

Instead:

```text
Authority references Concepts and Parameters.
```

Example:

```yaml
edges:
  - type: defines_parameter_values_for
    target: PARAM-allowable-stress

  - type: constrains_parameter
    target: PARAM-corrosion-allowance

  - type: references_concept
    target: CONCEPT-pressure
```

This preserves the principle:

```text
Standards reference ontology.
They do not redefine ontology.
```

---

# Relationship to material tables

A material table should be treated as an authority-owned table node.

Example:

```text
AUTH-ASTM-A106
  └── contains_table
      └── TABLE-ASTM-A106-chemical-composition

AUTH-ASME-B31.3
  └── contains_table
      └── TABLE-B313-allowable-stress
```

The lookup node consumes Facts and reads the table.

```text
Fact: material_specification = ASTM A106 Grade B
Fact: design_temperature = 400°F

↓ lookup

TABLE-B313-allowable-stress

↓ produces

Fact: allowable_stress = X
```

The Authority node defines where the table comes from.  
The Lookup node defines how the table is used.  
The Fact records the result.

---

# Forbidden fields

Authority nodes must not contain:

```yaml
runtime_value:
fact_value:
execution_id:
task_id:
selected_for_execution:
active_in_context:
calculation_result:
user_input:
```

Those belong to Authority Context, Execution Context, or Facts.

---

# Validation rules

An Authority node is invalid if:

1. `id` does not start with `AUTH-`.
    
2. `type` is not `authority`.
    
3. `key` is missing or not unique.
    
4. `authority_class` is missing.
    
5. It stores runtime execution state.
    
6. It duplicates paragraph or table content instead of referencing it.
    
7. It defines project-specific precedence as universal truth.
    
8. It contains calculated values from an execution.
    
9. It redefines Concepts or Parameters instead of referencing them.
    
10. It references unknown Paragraph, Table, Rule, Concept, or Parameter nodes.
    

---

# Conceptual rule

```text
Authority defines source.
Paragraph defines authoritative statement.
Table defines authoritative data.
Concept defines semantic meaning.
Parameter defines contextual engineering role.
Fact records runtime value.
Authority Context selects active authority for execution.
```