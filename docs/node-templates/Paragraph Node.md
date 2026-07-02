# Paragraph Node Template

> **Implementation:** B31.3 paragraph sources at [`knowledge/standards/asme/asme_b31.3/nodes/paragraph/`](../../knowledge/standards/asme/asme_b31.3/nodes/paragraph/) (on-disk ids such as `304.1.1`, not `B313-*`). Validator: [`engine/validation/paragraph_node_validator.py`](../../engine/validation/paragraph_node_validator.py). Executor-critical legacy fields (nomenclature, interactions, inputs, equations) live in sidecars under `paragraph/{id}/nomenclature.yaml` and `paragraph/{id}/execution.yaml`, merged at load time by [`engine/reference/paragraph_sidecar.py`](../../engine/reference/paragraph_sidecar.py) and [`engine/graph/graph_builder.py`](../../engine/graph/graph_builder.py). Runtime `B313-*` ids are aliases only — see [`engine/reference/b313_legacy_aliases.py`](../../engine/reference/b313_legacy_aliases.py). Linked authority: [`Authority Node`](Authority%20Node.md) (`AUTH-ASME-B31.3`).

## Canonical edge mapping (template → stored YAML)

On-disk YAML uses native taxonomy edge types. Legacy transport is accepted only via migration/import.

| Template edge | Stored `edges` entry |
|---------------|----------------------|
| `belongs_to_authority` | `{type: belongs_to_authority, target: AUTH-*}` |
| `introduces_parameter` | `{type: introduces_parameter, target: PARAM-*}` or virtual `param-*` from nomenclature |
| `references_equation` | `{type: references_equation, target: <equation-node-id>}` |
| `references_table` | `{type: references_table, target: <table-node-id>}` |
| `depends_on` | `{type: depends_on, target: ...}` or `{type: related_to, target: ...}` |
| Section parent | `{type: parent, target: <paragraph-number>}` |

See [`_relationship_schema.md`](_relationship_schema.md) for the full edge vocabulary and legacy import map.

A Paragraph node represents a specific authoritative statement, clause, section, note, or subsection from an Authority.

A Paragraph belongs to an Authority.  
A Paragraph may introduce Parameters, reference Concepts, constrain Equations, define applicability, and justify engineering decisions.

A Paragraph does **not** store runtime values.  
A Paragraph does **not** execute calculations by itself.  
A Paragraph is an authority anchor.

```yaml
---
id: B313-304.1.2
type: paragraph

key: b313_304_1_2
title: Straight Pipe Under Internal Pressure

authority: AUTH-ASME-B31.3
edition: 2024

paragraph_number: "304.1.2"
section: "304"
subsection: "304.1.2"

paragraph_class: calculation_requirement

description: >
  Defines the internal pressure design thickness equation and applicability
  requirements for straight pipe subject to internal pressure.

introduced_parameters:
  - PARAM-design-pressure
  - PARAM-outside-diameter
  - PARAM-allowable-stress
  - PARAM-weld-joint-efficiency
  - PARAM-weld-strength-reduction-factor-W
  - PARAM-temperature-coefficient-Y
  - PARAM-required-wall-thickness

referenced_concepts:
  - CONCEPT-pressure
  - CONCEPT-wall-thickness
  - CONCEPT-temperature
  - CONCEPT-material
  - CONCEPT-weld-joint

referenced_equations:
  - EQ-B313-wall-thickness

applicability:
  applies_when:
    - parameter: PARAM-pressure-loading
      operator: equals
      value: internal_pressure

    - parameter: PARAM-straight-pipe-section
      operator: equals
      value: true

limitations:
  - id: LIMIT-B313-thin-wall
    description: >
      Thin-wall equation is applicable only when the calculated thickness
      satisfies the applicable thickness-to-diameter criterion.
    related_parameter: PARAM-thin-wall-applicability

dependencies:
  - type: requires_lookup
    target: LOOKUP-B313-material-allowable-stress

  - type: references_paragraph
    target: B313-302.3.5

edges:
  - type: belongs_to_authority
    target: AUTH-ASME-B31.3

  - type: introduces_parameter
    target: PARAM-required-wall-thickness

  - type: references_concept
    target: CONCEPT-wall-thickness

  - type: references_equation
    target: EQ-B313-wall-thickness

  - type: depends_on
    target: B313-302.3.5

metadata:
  status: active
  node_version: 1
  source_revision_year: 2024
---

# Paragraph Text

[Insert exact standard paragraph text here.]

---

# Engineering Notes

[Optional internal explanation. Must not replace or alter the authoritative text.]
```

---

# Purpose

A Paragraph node answers:

```text
Which authoritative statement supports this engineering requirement, equation, limitation, or decision?
```

Examples:

```text
ASME B31.3 §304.1.1
ASME B31.3 §304.1.2
ASME B31.3 §302.3.5
API 570 inspection interval clause
ASTM A106 chemical composition requirement
```

Paragraphs are not generic content blocks.  
They are traceability anchors for engineering authority.

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Stable paragraph identity.|
|`type`|Must be `paragraph`.|
|`key`|Machine-safe paragraph key.|
|`title`|Human-readable title.|
|`authority`|Parent `AUTH-*` node.|
|`edition`|Authority edition used for this paragraph text.|
|`paragraph_number`|Official paragraph, clause, or section number.|
|`paragraph_class`|Role of the paragraph.|
|`description`|Short engineering description.|
|`metadata.source_revision_year`|Published standard year.|

---

# Recommended `paragraph_class` values

```yaml
definition
calculation_requirement
lookup_requirement
applicability_requirement
validation_requirement
limitation
exception
note
table_reference
figure_reference
inspection_requirement
testing_requirement
acceptance_criteria
reporting_requirement
```

---

# Paragraph vs Authority

```text
Authority = source document or governing source.
Paragraph = specific authoritative statement inside that source.
```

Example:

```text
AUTH-ASME-B31.3
  └── B313-304.1.2
```

The Authority tells us where the requirement comes from.  
The Paragraph tells us the exact clause used.

---

# Paragraph vs Concept

A Paragraph may mention or introduce a Concept, but it does not own the Concept.

Example:

```yaml
referenced_concepts:
  - CONCEPT-pressure
  - CONCEPT-wall-thickness
```

Correct:

```text
ASME B31.3 references the concept of pressure.
```

Incorrect:

```text
ASME B31.3 owns the concept of pressure.
```

---

# Paragraph vs Parameter

A Paragraph may introduce a Parameter in a standard-specific context.

Example:

```yaml
introduced_parameters:
  - PARAM-design-pressure
  - PARAM-required-wall-thickness
```

This means the Paragraph uses or defines the role of those Parameters within the standard.

It does not mean runtime values live in the Paragraph.

---

# Paragraph vs Equation

A Paragraph may reference or authorize an Equation.

Example:

```yaml
referenced_equations:
  - EQ-B313-wall-thickness
```

The Paragraph provides authority.  
The Equation provides deterministic mathematical structure.  
The Execution Layer evaluates the Equation using Facts.

---

# Paragraph text

The exact paragraph text should live below the frontmatter.

```markdown
# Paragraph Text

[Exact standard paragraph text.]
```

This supports:

```text
traceability
audit
reporting
human review
authority chain explanation
```

The Paragraph Text should not be paraphrased inside the authoritative text block.

Optional explanation may be added separately:

```markdown
# Engineering Notes
```

Engineering Notes are not authority.  
They are interpretation aids.

---

# Applicability model

Paragraph applicability should be structured.

```yaml
applicability:
  applies_when:
    - parameter: PARAM-pressure-loading
      operator: equals
      value: internal_pressure

  does_not_apply_when:
    - parameter: PARAM-pressure-loading
      operator: equals
      value: external_pressure
```

Recommended operators:

```yaml
equals
not_equals
greater_than
greater_than_or_equal
less_than
less_than_or_equal
in
not_in
exists
not_exists
```

Applicability is evaluated during planning, graph expansion, validation, or execution readiness.

---

# Limitations model

Limitations should be structured and traceable.

```yaml
limitations:
  - id: LIMIT-B313-thin-wall
    description: >
      Thin-wall equation is only valid when the required condition is satisfied.
    related_parameter: PARAM-thin-wall-applicability
    severity: blocking
```

Recommended severities:

```yaml
info
warning
blocking
requires_override
```

---

# Exceptions model

```yaml
exceptions:
  - id: EXCEPTION-B313-external-pressure
    description: >
      This paragraph does not govern external pressure design.
    redirects_to: B313-304.1.3
```

Exceptions should not be hidden in prose only.  
They should be machine-readable when they affect execution path.

---

# Example: definition paragraph

```yaml
---
id: B313-304.1.1
type: paragraph

key: b313_304_1_1
title: Straight Pipe General Requirements

authority: AUTH-ASME-B31.3
edition: 2024

paragraph_number: "304.1.1"
paragraph_class: definition

description: >
  Introduces general requirements and nomenclature for pressure design
  thickness of straight pipe.

introduced_parameters:
  - PARAM-required-wall-thickness
  - PARAM-corrosion-allowance
  - PARAM-minimum-required-thickness

referenced_equations:
  - EQ-B313-minimum-required-thickness

edges:
  - type: belongs_to_authority
    target: AUTH-ASME-B31.3

  - type: introduces_parameter
    target: PARAM-corrosion-allowance

  - type: references_equation
    target: EQ-B313-minimum-required-thickness

metadata:
  status: active
  node_version: 1
  source_revision_year: 2024
---

# Paragraph Text

[Exact paragraph text.]
```

---

# Example: material standard paragraph

```yaml
---
id: ASTM-A106-chemical-composition
type: paragraph

key: astm_a106_chemical_composition
title: Chemical Composition Requirements

authority: AUTH-ASTM-A106
edition: 2024

paragraph_number: "Chemical Composition"
paragraph_class: material_requirement

description: >
  Defines chemical composition limits for ASTM A106 material grades.

referenced_concepts:
  - CONCEPT-material
  - CONCEPT-chemical-composition

introduced_parameters:
  - PARAM-carbon-content
  - PARAM-manganese-content
  - PARAM-phosphorus-content
  - PARAM-sulfur-content

referenced_tables:
  - TABLE-ASTM-A106-chemical-composition

edges:
  - type: belongs_to_authority
    target: AUTH-ASTM-A106

  - type: references_table
    target: TABLE-ASTM-A106-chemical-composition

  - type: constrains_parameter
    target: PARAM-carbon-content

metadata:
  status: active
  node_version: 1
  source_revision_year: 2024
---

# Paragraph Text

[Exact source text.]
```

---

# Allowed relationships

Paragraph nodes may use:

```yaml
belongs_to_authority
references_concept
introduces_parameter
defines_requirement
references_equation
references_table
references_figure
depends_on
constrains_parameter
validates_parameter
redirects_to
supersedes
superseded_by
```

Example:

```yaml
edges:
  - type: belongs_to_authority
    target: AUTH-ASME-B31.3

  - type: introduces_parameter
    target: PARAM-design-pressure

  - type: references_equation
    target: EQ-B313-wall-thickness

  - type: references_table
    target: TABLE-B313-allowable-stress
```

---

# Report behavior

A Paragraph should appear in reports when it:

```text
authorized a calculation
introduced a required Parameter
defined an applicability condition
created a warning or limitation
provided a table or equation reference
affected a decision path
```

Reports should show:

```text
authority name
edition
paragraph number
title
reason used
relevant text or controlled excerpt
related equation/table/decision
```

---

# Forbidden fields

Paragraph nodes must not contain runtime execution state.

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

Paragraphs also should not contain canonical Concept or Parameter definitions except through references.

---

# Validation rules

A Paragraph node is invalid if:

1. `type` is not `paragraph`.
    
2. It has no parent Authority.
    
3. It has no paragraph number, clause identifier, or equivalent source locator.
    
4. It stores runtime values.
    
5. It duplicates Authority-level metadata unnecessarily.
    
6. It redefines Concepts instead of referencing them.
    
7. It redefines Parameters instead of introducing or referencing them.
    
8. It references an Equation without an authority relationship when the Equation is standard-derived.
    
9. It has machine-relevant applicability or exceptions only in prose.
    
10. It lacks source edition metadata.
    

---

# Conceptual rule

```text
Authority defines the source.
Paragraph defines the authoritative statement.
Concept defines engineering meaning.
Parameter defines contextual engineering role.
Equation defines deterministic relationship.
Fact records runtime value.
Report explains which Paragraph justified the result.
```