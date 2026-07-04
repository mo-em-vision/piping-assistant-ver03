# Authority Context Template

> **Implementation:** [`models/authority_context.py`](../../models/authority_context.py) on each `Task` as `authority_context` (peer to `execution_context`). Linked via `authority_context_id` / `execution_context_id`. Not a knowledge-graph node type.

An Authority Context defines the active governing sources for a specific engineering execution.

`active_authorities[].authority_id` references canonical [`Authority Node`](Authority%20Node.md) identities (`AUTH-*`) from [`knowledge/global/authorities/`](../../knowledge/global/authorities/).

It determines which standards, editions, company rules, project specifications, tables, and authority hierarchy rules apply.

An Authority Context is runtime-specific.  
It does not replace Authority nodes or Paragraph nodes.  
It selects which authoritative sources are active for the current execution.

```yaml
---
id: AUTHCTX-2026-000001
type: authority_context

task_id: TASK-pipe-wall-thickness-001
project_id: PROJECT-refinery-line-12
execution_context_id: EXEC-2026-000001

status: active

active_authorities:
  - authority_id: AUTH-ASME-B31.3
    edition: 2024
    role: primary_design_code
    status: active

  - authority_id: AUTH-ASME-B36.10M
    edition: 2022
    role: dimensional_standard
    status: active

  - authority_id: AUTH-ASTM-A106
    edition: 2024
    role: material_specification
    status: active

authority_hierarchy:
  - level: 1
    authority_type: regulation
    precedence: highest

  - level: 2
    authority_type: project_specification

  - level: 3
    authority_type: company_standard

  - level: 4
    authority_type: design_code

  - level: 5
    authority_type: material_standard

  - level: 6
    authority_type: reference_standard

applicable_paragraphs:
  - B313-304.1.1
  - 304.1.2-a
  - 302.3.5-e

applicable_tables:
  - TABLE-B313-allowable-stress
  - TABLE-B313-Y-coefficient
  - TABLE-B36.10M-pipe-dimensions

conflicts: []

overrides: []

validation:
  status: active
  warnings: []
  errors: []

metadata:
  created: 2026-07-02T10:18:00Z
  modified: 2026-07-02T10:30:00Z
  version: 1
---
```

---

# Purpose

The Authority Context answers:

```text
Which engineering authorities govern this execution?
```

It defines the active authority environment for one task, workflow, project, or execution.

Examples:

```text
ASME B31.3 2024 governs pipe wall thickness.
ASME B36.10M governs pipe dimensions.
ASTM A106 governs material designation.
Company piping specification overrides default corrosion allowance.
Project design basis defines design pressure and design temperature.
```

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Runtime Authority Context identity.|
|`type`|Must be `authority_context`.|
|`task_id`|Task this Authority Context supports.|
|`execution_context_id`|Execution Context governed by this Authority Context.|
|`active_authorities`|Standards, specifications, regulations, or policies currently active.|
|`authority_hierarchy`|Precedence rules between authorities.|
|`status`|Current authority-context state.|
|`metadata`|Version and runtime timestamps.|

---

# Recommended status values

```yaml
draft
active
incomplete
conflict_detected
override_required
validated
superseded
invalidated
```

---

# Active authorities

The `active_authorities` section lists the governing sources.

```yaml
active_authorities:
  - authority_id: AUTH-ASME-B31.3
    edition: 2024
    role: primary_design_code
    status: active
```

Recommended roles:

```yaml
primary_design_code
inspection_code
material_specification
dimensional_standard
company_standard
project_specification
regulation
client_requirement
reference_standard
recommended_practice
```

---

# Authority hierarchy

Authority hierarchy defines precedence when multiple sources apply.

Example:

```yaml
authority_hierarchy:
  - level: 1
    authority_type: regulation
    precedence: highest

  - level: 2
    authority_type: project_specification

  - level: 3
    authority_type: company_standard

  - level: 4
    authority_type: design_code

  - level: 5
    authority_type: reference_standard
```

This allows the system to resolve cases such as:

```text
Project specification requires 3 mm corrosion allowance.
ASME minimum calculation requires only 1.2 mm.
Project specification governs because it is higher in the project authority hierarchy.
```

---

# Applicable paragraphs

The Authority Context may record the paragraphs that became active during execution.

```yaml
applicable_paragraphs:
  - B313-304.1.1
  - 304.1.2-a
```

This list is not necessarily known at task creation.  
It may be populated as the Planner, Graph Engine, and Validation Layer discover applicable authority.

---

# Applicable tables

Tables are authority sources too.

```yaml
applicable_tables:
  - TABLE-B313-allowable-stress
  - TABLE-B36.10M-pipe-dimensions
```

A table should not be treated as a free-floating database.  
It should always remain connected to the authority that created it.

---

# Conflict model

Authority conflicts must be explicit.

```yaml
conflicts:
  - id: AUTHCONFLICT-001
    conflict_type: requirement_conflict

    authorities:
      - AUTH-COMPANY-PIPING-SPEC
      - AUTH-ASME-B31.3

    description: >
      Company specification requires a larger corrosion allowance than
      the minimum value used in the base ASME calculation.

    resolution:
      status: resolved
      selected_authority: AUTH-COMPANY-PIPING-SPEC
      reason: >
        Company specification has higher precedence within this project.
```

Recommended conflict types:

```yaml
requirement_conflict
edition_conflict
unit_basis_conflict
scope_conflict
material_classification_conflict
calculation_method_conflict
acceptance_criteria_conflict
```

---

# Override model

Overrides record user-accepted deviations or authority decisions.

```yaml
overrides:
  - id: AUTHOVERRIDE-001
    authority: AUTH-COMPANY-PIPING-SPEC
    affected_requirement: CORROSION_ALLOWANCE_MINIMUM
    original_requirement: 3 mm
    overridden_value: 2 mm
    approved_by: user
    reason: >
      Temporary screening calculation only. Final design requires formal review.
    report_required: true
```

Overrides must be visible in the final report.

---

# Example: ASME B31.3 wall thickness authority context

```yaml
---
id: AUTHCTX-B313-wall-thickness-001
type: authority_context

task_id: TASK-pipe-wall-thickness-001
execution_context_id: EXEC-pipe-wall-thickness-001

status: active

active_authorities:
  - authority_id: AUTH-ASME-B31.3
    edition: 2024
    role: primary_design_code
    status: active

  - authority_id: AUTH-ASME-B36.10M
    edition: 2022
    role: dimensional_standard
    status: active

  - authority_id: AUTH-ASTM-A106
    edition: 2024
    role: material_specification
    status: active

applicable_paragraphs:
  - B313-304.1.1
  - 304.1.2-a
  - 302.3.5-e

applicable_tables:
  - TABLE-B313-allowable-stress
  - TABLE-B313-Y-coefficient
  - TABLE-B36.10M-pipe-dimensions

authority_hierarchy:
  - level: 1
    authority_type: regulation

  - level: 2
    authority_type: project_specification

  - level: 3
    authority_type: company_standard

  - level: 4
    authority_type: design_code

  - level: 5
    authority_type: reference_standard

conflicts: []

overrides: []

validation:
  status: active
  warnings: []
  errors: []

metadata:
  created: 2026-07-02T10:18:00Z
  modified: 2026-07-02T10:30:00Z
  version: 1
---
```

---

# Relationship to Authority nodes

Authority Context is not the same as Authority.

```text
Authority Node:
  Defines an authoritative source.

Authority Context:
  Selects which Authority nodes are active during execution.
```

Example:

```text
AUTH-ASME-B31.3
  = canonical authority source

AUTHCTX-B313-wall-thickness-001
  = ASME B31.3 2024 is active for this task
```

---

# Relationship to Paragraph nodes

Paragraphs belong to Authority.

Authority Context determines whether those paragraphs are active.

```text
AUTH-ASME-B31.3
  └── Paragraph 304.1.2-a

AUTHCTX-001
  └── activates 304.1.2-a for this execution
```

---

# Relationship to Execution Context

The Execution Context records runtime state.

The Authority Context records governing authority.

```text
Execution Context:
  What happened?

Authority Context:
  Under which authority did it happen?
```

The two should reference each other but remain separate.

---

# Allowed relationships

Authority Context may connect to:

```yaml
activates_authority
activates_paragraph
activates_table
governs_execution_context
governs_goal
constrains_parameter
validates_fact
resolves_conflict
records_override
supersedes
```

Example:

```yaml
edges:
  - type: governs_execution_context
    target: EXEC-2026-000001

  - type: activates_authority
    target: AUTH-ASME-B31.3

  - type: activates_paragraph
    target: 304.1.2-a

  - type: activates_table
    target: TABLE-B313-allowable-stress
```

---

# Forbidden fields

Authority Context must not contain:

```yaml
calculation_result:
fact_value:
unit_conversion_rule:
parameter_definition:
concept_definition:
equation_formula:
full_standard_text:
```

Those belong to Facts, Units, Parameters, Concepts, Equations, and Paragraph nodes.

---

# Validation rules

An Authority Context is invalid if:

1. `type` is not `authority_context`.
    
2. It has no active authority for a standards-governed execution.
    
3. It references an unknown authority.
    
4. It references a paragraph whose parent authority is not active.
    
5. It references a table whose parent authority is not active.
    
6. It has unresolved conflicts but reports `status: validated`.
    
7. It records an override without reason or provenance.
    
8. It allows execution under multiple conflicting authority editions without resolution.
    
9. It stores runtime calculation values.
    
10. It replaces Authority nodes instead of selecting them.
    

---

# Conceptual rule

```text
Authority defines what is permitted.
Knowledge defines what is possible.
Execution records what happened.
Authority Context records what governed the execution.
```