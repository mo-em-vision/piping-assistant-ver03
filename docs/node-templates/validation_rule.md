# Validation Rule Node Template

> **Implementation:** Validator: [`engine/validation/validation_rule_node_validator.py`](../../engine/validation/validation_rule_node_validator.py). On-disk graph edges use taxonomy types (`authorized_by`, `requires_parameter`, `validates_parameter`, `constrains_equation`, …). See [`Relationship Taxonomy.md`](Relationship%20Taxonomy.md) and [`_relationship_schema.md`](_relationship_schema.md).

A Validation Rule node defines a deterministic pass/fail check, applicability gate, or limit check.

A Validation Rule consumes input Parameters through runtime Facts.  
It produces validation results (not calculated engineering quantities).

For table resolution use [`lookup.md`](lookup.md).  
For formula calculations use [`equation node.md`](equation%20node.md).

Do **not** author a top-level `links` metadata block — object relationships belong in typed `edges` only ([`_relationship_schema.md`](_relationship_schema.md#on-disk-rule)). **Exception:** declare governing paragraphs in `authority.authorized_by` (not in `edges`); the graph compiler emits `authorized_by` edges at build time.

```yaml
---
id: VALRULE-B313-thin-wall-check
type: validation_rule

key: b313_thin_wall_check
name: Thin-Wall Applicability Check

rule_class: validation

description: >
  Checks whether the calculated wall thickness satisfies the thin-wall
  applicability criterion.

authority:
  authorized_by:
    - 304.1.2-a
  authority_context_required: true

display:
  text: "t < D / 6"

expression:
  language: sympy
  formula: "thin_wall_valid = t < D / 6"

requires:
  - parameter: PARAM-required-wall-thickness
    symbol: t
    required: true
    dimension: DIM-length

  - parameter: PARAM-outside-diameter
    symbol: D
    required: true
    dimension: DIM-length

validates:
  - parameter: PARAM-thin-wall-applicability
    symbol: thin_wall_valid
    dimension: null

on_fail:
  severity: error
  blocks_goal: true
  creates_warning: TEXT-thin-wall-warning

edges:
  - type: requires_parameter
    target: PARAM-required-wall-thickness

  - type: requires_parameter
    target: PARAM-outside-diameter

  - type: validates_parameter
    target: PARAM-thin-wall-applicability

  - type: constrains_equation
    target: EQ-B313-wall-thickness

metadata:
  status: active
  version: 1
---
```

---

# Purpose

A Validation Rule answers:

```text
Does this engineering state satisfy an authority requirement, limit, or applicability condition?
```

Examples:

```text
t < D / 6  (thin-wall applicability)
A_2 + A_3 + A_4 >= A_1  (reinforcement adequacy)
design_temperature <= material_limit
```

A Validation Rule does not store runtime values.  
It defines the check used to produce validation findings at execution time.

---

# Required fields

| Field | Purpose |
|-------|---------|
| `id` | Stable identity. Must use `VALRULE-*` or pack convention (e.g. `asme_b313_*_valrule_*`). |
| `type` | Must be `validation_rule`. |
| `key` | Machine-safe rule key. |
| `name` | Human-readable rule name. |
| `rule_class` | Must be `validation` (distinct from future general `rule` nodes). |
| `description` | Stable engineering description. |
| `requires` | Input Parameters required by the check. |
| `validates` | Parameter(s) under test or boolean adequacy output. |
| `metadata` | Status and versioning. |

---

# Validation Rule vs Equation

| | Equation (`EQ-*`) | Validation Rule (`VALRULE-*`) |
|--|-------------------|-------------------------------|
| Purpose | Calculate engineering quantities | Check limits, applicability, adequacy |
| Output edge | `calculates_parameter` | `validates_parameter` |
| Produces | Derived Facts (numeric results) | Validation findings / pass-fail |

Do not model validation checks as `equation` nodes with `equation_class: validation`.

---

# Allowed relationships

Validation rule nodes may use these edge types on `edges`:

```yaml
requires_parameter
validates_parameter
constrains_equation
creates_warning
supersedes
superseded_by
```

Governing paragraphs belong in `authority.authorized_by` — not as `authorized_by` edges.

Runtime-only edges (execution models, not knowledge YAML):

```yaml
produces_validation_result
blocks_goal
```

---

# Forbidden fields

Validation rule nodes must not contain runtime execution values.

Forbidden:

```yaml
runtime_value:
fact_value:
user_input:
execution_id:
task_id:
calculation_result:
selected_for_execution:
active_in_context:
```

---

# Validation rules

A Validation Rule node is invalid if:

1. `type` is not `validation_rule`.
2. `rule_class` is not `validation`.
3. It has no `requires` list when inputs are required.
4. It has no `validates` list.
5. It uses `calculates_parameter` instead of `validates_parameter`.
6. It stores runtime values.
7. It has no authorizing Paragraph when derived from a standard.

---

# Example: reinforcement adequacy (eq. 6a)

```yaml
---
id: VALRULE-B313-reinforcement-adequacy-6a
type: validation_rule

key: asme_b313_304_3_3_valrule_6a
name: Available Reinforcement Area Check

rule_class: validation

description: >
  Verifies available reinforcement area A_2 + A_3 + A_4 is at least the
  required area A_1 per ASME B31.3 eq. (6a).

authority:
  authorized_by:
    - 304.3.3-c
  authority_context_required: true

display:
  text: "A_2 + A_3 + A_4 >= A_1"

expression:
  language: sympy
  formula: "reinforcement_adequate = (A_2 + A_3 + A_4) >= A_1"

requires:
  - parameter: PARAM-A-2
    symbol: A_2
    required: true
  - parameter: PARAM-A-3
    symbol: A_3
    required: true
  - parameter: PARAM-A-4
    symbol: A_4
    required: true
  - parameter: PARAM-A-1
    symbol: A_1
    required: true

validates:
  - parameter: PARAM-reinforcement-adequate
    symbol: reinforcement_adequate

edges:
  - type: validates_parameter
    target: PARAM-reinforcement-adequate

metadata:
  status: active
  version: 1
---
```
