# Authority Context Runtime Contract

## Purpose

An **Authority Context** defines which governing engineering sources are **active** for a specific task run — design codes, material standards, company rules, project specifications, and their precedence. It selects from immutable **Authority** nodes (`AUTH-*`) in the knowledge graph; it does not replace them.

It answers: *"Under which authority is this execution governed?"*

## What it is

| Aspect | Detail |
| --- | --- |
| **Layer** | Runtime model on `Task` |
| **Storage** | `Task.authority_context` ([`models/authority_context.py`](../../../models/authority_context.py)) |
| **Type** | `type: authority_context` |
| **Mutable** | Yes — paragraphs/tables may be discovered during execution |
| **Authored in `knowledge/`?** | **No** — configured per task; references `AUTH-*` nodes from `knowledge/global/authorities/` |

```text
Authority Node (knowledge):  AUTH-ASME-B31.3     →  canonical source definition
Authority Context (runtime): active B31.3 2024   →  selected for this task
```

### Conceptual rule

```text
Authority defines what is permitted.
Knowledge defines what is possible.
Execution records what happened.
Authority Context records what governed the execution.
```

### Authority Node vs Authority Context

| | Authority Node | Authority Context |
| --- | --- | --- |
| **Location** | `knowledge/global/authorities/` | On `Task` at runtime |
| **Contract** | [Authority Node](../nodes/authority.md) | This document |
| **Role** | Defines an authoritative source | Selects which sources are active |
| **Example** | `AUTH-ASME-B31.3` | `AUTHCTX-B313-wall-thickness-001` activates B31.3 2024 |

Paragraphs belong to Authority nodes. The Authority Context records which paragraphs and tables became applicable during the run.

## Key fields

### Required top-level fields

| Field | Purpose |
| --- | --- |
| `id` | Runtime identity (e.g. `AUTHCTX-2026-000001`) |
| `type` | Must be `authority_context` |
| `task_id` | Task this context supports |
| `execution_context_id` | Linked [Execution Context](execution-context.md) |
| `active_authorities` | Standards/specs currently governing the run |
| `authority_hierarchy` | Precedence order when sources conflict |
| `status` | Authority-context lifecycle state |
| `metadata` | Created/modified timestamps, version |

### Optional fields

| Field | Purpose |
| --- | --- |
| `project_id` | Project scope |
| `applicable_paragraphs` | Paragraph ids activated during execution (may grow over time) |
| `applicable_tables` | Table ids tied to active authorities |
| `conflicts` | Explicit authority conflicts and resolutions |
| `overrides` | User-approved deviations (must appear in reports) |
| `validation` | Authority-context validation state |

### `status` values

```text
draft, active, incomplete, conflict_detected, override_required,
validated, superseded, invalidated
```

### `active_authorities` entry

```yaml
active_authorities:
  - authority_id: AUTH-ASME-B31.3
    edition: "2024"
    role: primary_design_code
    status: active
```

**Recommended `role` values:**

```text
primary_design_code, inspection_code, material_specification,
dimensional_standard, company_standard, project_specification,
regulation, client_requirement, reference_standard, recommended_practice
```

`authority_id` must reference a canonical [`AUTH-*` Authority node](../nodes/authority.md).

### `authority_hierarchy` model

Defines precedence when multiple sources apply:

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
    authority_type: material_standard
  - level: 6
    authority_type: reference_standard
```

Example resolution: project specification requires 3 mm corrosion allowance; ASME minimum is 1.2 mm — project spec wins when higher in hierarchy.

### `applicable_paragraphs` and `applicable_tables`

Populated as Planner, Graph Engine, and Validation discover governing content — not necessarily known at task creation:

```yaml
applicable_paragraphs:
  - 304.1.2-a
  - 302.3.5-e
applicable_tables:
  - TABLE-B313-allowable-stress
  - TABLE-B36.10M-pipe-dimensions
```

Tables must remain connected to the authority that created them.

### `conflicts` model

```yaml
conflicts:
  - id: AUTHCONFLICT-001
    conflict_type: requirement_conflict
    authorities:
      - AUTH-COMPANY-PIPING-SPEC
      - AUTH-ASME-B31.3
    description: Company spec requires larger corrosion allowance than ASME minimum.
    resolution:
      status: resolved
      selected_authority: AUTH-COMPANY-PIPING-SPEC
      reason: Company specification has higher precedence.
```

**`conflict_type` values:**

```text
requirement_conflict, edition_conflict, unit_basis_conflict, scope_conflict,
material_classification_conflict, calculation_method_conflict,
acceptance_criteria_conflict
```

### `overrides` model

```yaml
overrides:
  - id: AUTHOVERRIDE-001
    authority: AUTH-COMPANY-PIPING-SPEC
    affected_requirement: CORROSION_ALLOWANCE_MINIMUM
    original_requirement: 3 mm
    overridden_value: 2 mm
    approved_by: user
    reason: Temporary screening calculation only.
    report_required: true
```

Overrides must be visible in the final report.

## Relationships

| Relationship | Target | Meaning |
| --- | --- | --- |
| `governs_execution_context` | `EXEC-*` | Paired [Execution Context](execution-context.md) |
| `activates_authority` | `AUTH-*` | Authority node active for this run |
| `activates_paragraph` | paragraph id | Governing paragraph in scope |
| `activates_table` | `TABLE-*` | Governing table in scope |
| `governs_goal` | `GOAL-*` | Goal requiring authority alignment |
| `constrains_parameter` | `PARAM-*` | Parameter governed by active authority |
| `validates_fact` | `FACT-*` | Fact checked against authority rules |
| `resolves_conflict` | conflict id | Recorded resolution |
| `records_override` | override id | Approved deviation |
| `supersedes` | `AUTHCTX-*` | Replaced authority context |

### Peer link to Execution Context

```text
Execution Context:   What happened?
Authority Context:   Under which authority did it happen?
```

Cross-reference fields:

- `execution_context.authority_context_id` → this context's `id`
- `authority_context.execution_context_id` → paired execution context `id`

Related contracts:

- [Execution Context](execution-context.md) — runtime state governed by this context
- [Goal](goal.md) — may reference authority via `authority.references`
- [Fact](fact.md) — values validated under active authorities
- [Authority Node](../nodes/authority.md) — immutable `AUTH-*` definitions

## What NOT to put here

Authority Context must **not** store engineering results or definitions:

```text
calculation_result, fact_value, unit_conversion_rule, parameter_definition,
concept_definition, equation_formula, full_standard_text
```

Those belong on Facts, Units, Parameters, Concepts, Equations, and Paragraph nodes.

### Invalid Authority Context conditions

1. `type` is not `authority_context`
2. No active authority for a standards-governed execution
3. References an unknown `AUTH-*` authority
4. References a paragraph whose parent authority is not active
5. References a table whose parent authority is not active
6. Unresolved conflicts but `status: validated`
7. Override without reason or provenance
8. Multiple conflicting authority editions without resolution
9. Stores runtime calculation values
10. Replaces Authority nodes instead of selecting them

## Implementation reference

| Module | Role |
| --- | --- |
| [`models/authority_context.py`](../../../models/authority_context.py) | `AuthorityContext` dataclass, `ActiveAuthority`, hierarchy, conflict/override types, factory helpers |
| [`models/execution_context.py`](../../../models/execution_context.py) | Holds `authority_context_id` linking to this context |
| [`models/task.py`](../../../models/task.py) | Each `Task` owns `authority_context` as peer to `execution_context` |

**On Task:** `task.authority_context` is configured when a standards-governed workflow starts and updated as applicable paragraphs/tables are discovered.

**Knowledge reference:** [`knowledge/global/authorities/`](../../../knowledge/global/authorities/) — immutable `AUTH-*` nodes selected by this context.

**Migration note:** Consolidated from former `docs/node-templates/` runtime templates (removed).
