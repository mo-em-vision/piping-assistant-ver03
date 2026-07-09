# Paragraph Node 

A Paragraph node represents one exact subdivision of an authoritative source.

A Paragraph node is an authority text anchor.

It stores the original standard text and connects that text to related engineering objects via typed `edges` (Concepts, Parameters, Equations, Lookups, Tables, Validation Rules, and other Paragraphs).

A Paragraph node should not contain runtime values, calculation results, execution state, or excessive interpretation.

```yaml
---
id: 304.1.2-a
type: paragraph

key: b313_304_1_2_a
authority: AUTH-ASME-B31.3
edition: 2024

paragraph_number: 304.1.2-a
title: Straight Pipe Under Internal Pressure — Thin Wall

text:
  original: >
    [Insert exact original paragraph text here.]

hierarchy:
  parent: '304.1'
  children: []

edges:
  - type: belongs_to_authority
    target: AUTH-ASME-B31.3

  - type: references_concept
    target: CONCEPT-pressure

  - type: references_parameter
    target: PARAM-design-pressure

  - type: references_equation
    target: EQ-B313-wall-thickness

metadata:
  status: active
  source_revision_year: 2024
  node_version: 1
  last_revision: 2026-07-04
  edited_by: admin

presentation:
  summary: >
    Short user-facing explanation for the center-panel scroll (1–3 sentences).
  display_label: Optional heading override for scroll blocks
  reference_label: Optional chip label override (defaults to § paragraph number)
---
```

---

# Subsection naming

ASME B31.3 pack paragraph ids use **bare ids** (no `B313-` prefix). Lettered subsections use a hyphen suffix.

| Concept | Rule | Example |
| --- | --- | --- |
| `id` / filename | `{section}-{lowercase_letter}` | `304.1.2-a`, `302.3.5-e` |
| `paragraph_number` | Same as `id` | `304.1.2-a` — not `304.1.2(a)` |
| `key` | Underscore machine key | `b313_304_1_2_a` |
| `text.original` prose | Official citation with parentheses is fine | `**(a)**` in body text |
| `edges[].target` | Subsection node id | `302.3.5-e` — not `302.3.5` + `subsection: e` |
| Unlettered paragraph | Single unsuffixed id | `304.1.3` |
| Preamble before (b) | Unsuffixed base + lettered children | `304.3.1`, `304.3.1-b`, `304.3.1-c` |

**Edge targets:** use the full lettered paragraph `id` in `target`. Do **not** add a separate `subsection` field on edges when a dedicated paragraph node exists (e.g. `target: 302.3.5-e`, not `target: 302.3.5` with `subsection: e`).

**Hierarchy traversal** (parent chain and children) belongs in the `hierarchy` block only:

```yaml
hierarchy:
  parent: '304.1'
  children: []
```

Sibling read order is the **ordered `children` list on the parent** section node (e.g. `304.1` lists `304.1.1-a`, `304.1.1-b`, `304.1.2-a`, …). Do **not** author `hierarchy.previous` or `hierarchy.next`.

Do **not** use `related_to` edges for parent/sibling sequencing. Do **not** add `parent`, `child`, `next`, or `previous` graph edges on paragraph nodes — use `hierarchy` metadata only. Workflow execution order uses **workflow** `next` edges.

See also [`.cursor/rules/paragraph-subsection-naming.mdc`](../../.cursor/rules/paragraph-subsection-naming.mdc).

---

# Purpose

A Paragraph node answers:

```text
What does the original authority text say, and what engineering objects is this text connected to?
```

It should not answer:

```text
How is this equation executed?
How is this table queried?
Is this execution compliant?
Which branch is currently active?
What value did the user provide?
```

Those belong to other nodes.

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Stable paragraph node identity.|
|`type`|Must be `paragraph`.|
|`key`|Machine-safe key.|
|`authority`|Parent Authority node.|
|`edition`|Standard edition.|
|`paragraph_number`|Same as `id` (hyphen form for subsections).|
|`text.original`|Exact original paragraph text.|
|`metadata.source_revision_year`|Source revision year.|
|`metadata.last_revision`|ISO date of last content edit.|
|`metadata.edited_by`|Editor id (currently `admin`).|

---

# Recommended fields

|Field|Purpose|
|---|---|
|`title`|Short display title, if useful.|
|`hierarchy.parent`|Parent paragraph or section.|
|`hierarchy.children`|Child subsections (order = sibling read order).|
|`edges`|Typed graph relationships (sole linkage mechanism).|

---

# Paragraph granularity

Use one node per meaningful source subdivision.

Good:

```text
304.1.1-a
304.1.1-b
304.1.3
```

Avoid stuffing multiple independent subsections into one node.

Bad:

```text
B313-304.1
  contains all of 304.1.1, 304.1.2, 304.1.3, 304.1.4 as one large text block
```

Each subsection should be independently addressable because different subsections may connect to different Parameters, Equations, Tables, or Validation Rules.

---

# Nomenclature paragraphs

When `metadata.kind: nomenclature` (e.g. `304.1.1-b`), the paragraph **defines symbols only**. Author:

- `belongs_to_authority`
- `introduces_parameter` — one edge per symbol introduced in `text.original`

Do **not** author on nomenclature paragraphs:

- `references_table`, `references_concept`, `references_equation`, `related_to`
- a `links` metadata block (knowledge nodes use `edges` only)

Table and lookup relationships belong on the corresponding global [`PARAM-*`](../../knowledge/global/parameters/nodes/) nodes via `used_by` edges. Graph traversal reaches tables through `introduces_parameter` → `PARAM-*` → `used_by` → table/lookup.

Prose traces (e.g. W cites para. 302.3.5(e)) stay in the nomenclature sidecar `citations` block when they must not expand execution.

---

# Original text field

The Paragraph node should have a dedicated original text field:

```yaml
text:
  original: >
    [Exact original paragraph text.]
```

`source_language` is set once in the pack root [`pack.yaml`](../../knowledge/standards/asme/asme_b31.3/pack.yaml) and inherited by all child nodes at load time. Do **not** repeat it on paragraph nodes.

Do not hide the original text in free-form Markdown below the YAML



---

# Interpretation should live outside Paragraph nodes

Paragraph nodes should not contain heavy interpretation fields such as:

```yaml
paragraph_class:
applicability:
limitations:
exceptions:
calculation_logic:
validation_logic:
```

Those should move to dedicated nodes.

Use:

```text
Equation node
  for formulas

Lookup node
  for table lookup behavior

Validation Rule node
  for compliance/applicability checks

Applicability Rule node
  for branch activation logic

Table node
  for structured authority data

Workflow node
  for task patterns
```

The Paragraph connects to them via typed `edges`.

---

# Example: paragraph node with text and edges

```yaml
---
id: 304.1.2-a
type: paragraph

key: b313_304_1_2_a
authority: AUTH-ASME-B31.3
edition: 2024

paragraph_number: 304.1.2-a
title: Straight Pipe Under Internal Pressure — Thin Wall

text:
  original: >
    [Exact original paragraph text.]

hierarchy:
  parent: '304.1'
  children: []

edges:
  - type: belongs_to_authority
    target: AUTH-ASME-B31.3

  - type: references_concept
    target: CONCEPT-pressure

  - type: references_parameter
    target: PARAM-design-pressure

  - type: references_equation
    target: EQ-B313-wall-thickness

  - type: references_validation_rule
    target: VALRULE-B313-thin-wall-applicability

metadata:
  status: active
  source_revision_year: 2024
  node_version: 1
  last_revision: 2026-07-04
  edited_by: admin
---
```

---

# Relationship rule

Paragraph graph edges should be **typed references** to engineering objects, plus optional `related_to` for **cross-paragraph citations that appear in `text.original`**.

## `hierarchy` vs `edges`

| Concern | Where it lives | Examples |
| --- | --- | --- |
| Parent / children | `hierarchy` metadata only | `parent: '304.1'`, `children: [304.1.1-a, 304.1.1-b, …]` |
| Prose cross-reference to another paragraph | `related_to` edge only | Text cites “para. 304” → `related_to: '304'` |

**Do not** author a `links` metadata block — all object linkage belongs in typed `edges` ([`_relationship_schema.md`](_relationship_schema.md#on-disk-rule)). Use `related_to` for paragraph cross-references cited in `text.original` that should appear in the graph. Definitional back-references in nomenclature that must not expand execution may be omitted from `edges` when `hierarchy` already provides navigation context.

**Do not** use `related_to` for:

- parent/child structure (use `hierarchy.parent` / `hierarchy.children`)
- “see also” navigation when the authority text does not cite that paragraph

Runtime planners and hierarchy helpers resolve ancestor chains and subsection order from `hierarchy`, not from `related_to`.

## Recommended graph edge types

```yaml
belongs_to_authority
references_concept
references_parameter
references_equation
references_lookup
references_table
references_validation_rule
introduces_parameter
related_to                # only when text.original cites the target paragraph
```

**Forbidden** structural edge types on paragraph nodes: `parent`, `child`, `next`, `previous`.

Avoid stronger execution relationships from Paragraph nodes, such as:

```yaml
requires_parameter
calculates_parameter
validates_parameter
reads_table
```

Those belong to Equation, Lookup, Validation Rule, or Workflow nodes.

---

# Forbidden fields

Paragraph nodes must not contain:

```yaml
runtime_value:
fact_value:
execution_id:
task_id:
calculation_result:
lookup_result:
validation_result:
user_input:
current_status:
active_in_context:
```

Paragraph nodes also should not contain executable formulas, lookup rules, or validation conditions.

---

# Validation rules

A Paragraph node is invalid if:

1. `type` is not `paragraph`.
    
2. It has no parent `authority`.
    
3. It has no `paragraph_number`.
    
4. It has no `text.original`.
    
5. It stores runtime values.
    
6. It stores execution state.
    
7. It stores calculation results.
    
8. It contains executable lookup or validation logic.
    
9. It combines multiple independently addressable subsections into one node.
    
10. It references unknown Concepts, Parameters, Equations, Tables, Lookups, or Validation Rules.
    

---

# Conceptual rule

```text
Paragraph = original authority text and traceability anchor.

Equation = mathematical relationship.

Lookup = table query behavior.

Validation Rule = compliance or applicability check.

Table = authoritative structured data.

Fact = runtime value.

Authority Context = which authority is active during execution.
```