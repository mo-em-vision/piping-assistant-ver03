# Relationship Taxonomy

The Relationship Taxonomy defines the controlled vocabulary of graph edge types used across the Engineering Operating System.

Relationships must be explicit, typed, directional, and semantically meaningful.

Avoid generic relationships such as:

```yaml
type: references
```

unless no more specific relationship exists.

---

# Purpose

Relationships define how meaning flows through the graph.

A node by itself is only an isolated object.

A relationship explains:

```text
why one node connects to another
what the connection means
whether it affects execution
whether it affects authority
whether it affects reporting
whether it affects validation
```

---

# Core rule

Every edge must answer:

```text
What does this source node mean relative to this target node?
```

Bad:

```yaml
edges:
  - type: references
    target: PARAM-design-pressure
```

Better:

```yaml
edges:
  - type: requires_parameter
    target: PARAM-design-pressure
```

or:

```yaml
edges:
  - type: introduces_parameter
    target: PARAM-design-pressure
```

or:

```yaml
edges:
  - type: constrains_parameter
    target: PARAM-design-pressure
```

The correct relationship depends on meaning.

---

# Edge format

Recommended standard edge format:

```yaml
edges:
  - type: requires_parameter
    target: PARAM-design-pressure
    role: input
    required: true
    reason: >
      Design pressure is required as input to the wall thickness equation.
```

Minimum edge format:

```yaml
edges:
  - type: requires_parameter
    target: PARAM-design-pressure
```

---

# Relationship categories

Relationships are grouped into these categories:

```text
1. Ontology relationships
2. Parameter and Fact relationships
3. Authority relationships
4. Equation relationships
5. Workflow and Goal relationships
6. Execution relationships
7. Validation relationships
8. Report relationships
9. Lifecycle relationships
```

---

# 1. Ontology relationships

These describe semantic structure.

## `has_concept`

Connects a Parameter to its broader Concept.

```yaml
- type: has_concept
  target: CONCEPT-pressure
```

Allowed source nodes:

```text
parameter
```

Allowed target nodes:

```text
concept
```

Example:

```text
PARAM-design-pressure --has_concept--> CONCEPT-pressure
```

---

## `has_dimension`

Connects a Concept or Parameter to a Dimension.

```yaml
- type: has_dimension
  target: DIM-pressure
```

Allowed source nodes:

```text
concept
parameter
```

Allowed target nodes:

```text
dimension
```

Example:

```text
PARAM-design-pressure --has_dimension--> DIM-pressure
```

---

## `allows_unit`

Connects a Dimension to compatible Units.

```yaml
- type: allows_unit
  target: UNIT-bar
```

Allowed source nodes:

```text
dimension
```

Allowed target nodes:

```text
unit
```

Example:

```text
DIM-pressure --allows_unit--> UNIT-bar
```

---

## `belongs_to_dimension`

Connects a Unit to its Dimension.

```yaml
- type: belongs_to_dimension
  target: DIM-pressure
```

Allowed source nodes:

```text
unit
```

Allowed target nodes:

```text
dimension
```

---

## `converts_to`

Connects a Unit to its canonical conversion target.

```yaml
- type: converts_to
  target: UNIT-Pa
  factor: 6894.757293168
  offset: 0
```

Allowed source nodes:

```text
unit
```

Allowed target nodes:

```text
unit
```

---

## `property_of`

Connects a property Parameter to the Concept it describes.

```yaml
- type: property_of
  target: CONCEPT-material
```

Example:

```text
PARAM-material-density --property_of--> CONCEPT-material
PARAM-fluid-density --property_of--> CONCEPT-fluid
```

This allows `density` to remain its own Concept while also being applied to a specific engineering object.

---

## `specializes`

Connects a more specific Concept to a broader Concept.

```yaml
- type: specializes
  target: CONCEPT-pressure
```

Example:

```text
CONCEPT-internal-pressure --specializes--> CONCEPT-pressure
```

---

## `generalizes`

Inverse of `specializes`.

```yaml
- type: generalizes
  target: CONCEPT-internal-pressure
```

Use sparingly. Prefer `specializes` for consistency.

---

## `related_to`

Weak semantic association.

```yaml
- type: related_to
  target: CONCEPT-corrosion
```

Use only when no stronger relationship exists.

---

# 2. Parameter and Fact relationships

These connect concepts to runtime evidence.

## `instantiates`

Connects a Fact to the Parameter it gives a value to.

```yaml
- type: instantiates
  target: PARAM-design-pressure
```

Allowed source nodes:

```text
fact
```

Allowed target nodes:

```text
parameter
```

Example:

```text
FACT-design-pressure-001 --instantiates--> PARAM-design-pressure
```

---

## `derived_from`

Connects a derived Fact to input Facts.

```yaml
- type: derived_from
  target: FACT-design-pressure-001
```

Allowed source nodes:

```text
fact
```

Allowed target nodes:

```text
fact
```

Example:

```text
FACT-required-wall-thickness-001 --derived_from--> FACT-design-pressure-001
```

---

## `supersedes_fact`

Connects a newer Fact to the older Fact it replaces.

```yaml
- type: supersedes_fact
  target: FACT-design-temperature-001
```

Allowed source nodes:

```text
fact
```

Allowed target nodes:

```text
fact
```

---

## `conflicts_with_fact`

Connects two conflicting Facts.

```yaml
- type: conflicts_with_fact
  target: FACT-design-temperature-002
```

Conflicting Facts should be preserved until resolved.

---

## `satisfies_goal`

Connects a Fact to the Goal it satisfies.

```yaml
- type: satisfies_goal
  target: GOAL-required-wall-thickness-001
```

Allowed source nodes:

```text
fact
```

Allowed target nodes:

```text
goal
```

---

# 3. Authority relationships

These describe authority structure and traceability.

## `belongs_to_authority`

Connects Paragraphs, Tables, Figures, or Rules to their Authority.

```yaml
- type: belongs_to_authority
  target: AUTH-ASME-B31.3
```

Example:

```text
B313-304.1.2 --belongs_to_authority--> AUTH-ASME-B31.3
```

---

## `contains_paragraph`

Connects an Authority to a Paragraph.

```yaml
- type: contains_paragraph
  target: B313-304.1.2
```

---

## `contains_table`

Connects an Authority to a Table.

```yaml
- type: contains_table
  target: TABLE-B313-allowable-stress
```

---

## `contains_rule`

Connects an Authority to a Rule.

```yaml
- type: contains_rule
  target: RULE-B313-thin-wall-limit
```

---

## `references_authority`

Connects one Authority to another Authority it references.

```yaml
- type: references_authority
  target: AUTH-ASME-B36.10M
```

Example:

```text
ASME B31.3 may reference dimensional data from ASME B36.10M.
```

---

## `refines_authority`

Connects a more specific Authority to a broader one it refines.

```yaml
- type: refines_authority
  target: AUTH-ASME-B31.3
```

Example:

```text
Company Piping Specification --refines_authority--> ASME B31.3
```

---

## `conflicts_with_authority`

Connects authorities with known conflicting requirements.

```yaml
- type: conflicts_with_authority
  target: AUTH-ASME-B31.3
```

This does not resolve the conflict.  
Authority Context resolves conflict for a specific execution.

---

## `activates_authority`

Connects an Authority Context to an active Authority.

```yaml
- type: activates_authority
  target: AUTH-ASME-B31.3
```

Allowed source nodes:

```text
authority_context
```

Allowed target nodes:

```text
authority
```

---

## `activates_paragraph`

Connects an Authority Context to a Paragraph active in execution.

```yaml
- type: activates_paragraph
  target: B313-304.1.2
```

---

## `activates_table`

Connects an Authority Context to an active Table.

```yaml
- type: activates_table
  target: TABLE-B313-allowable-stress
```

---

# 4. Paragraph relationships

## `introduces_parameter`

Connects a Paragraph to a Parameter introduced or defined by that paragraph.

```yaml
- type: introduces_parameter
  target: PARAM-design-pressure
```

Example:

```text
B313-304.1.2 --introduces_parameter--> PARAM-design-pressure
```

---

## `references_concept`

Connects a Paragraph, Authority, Equation, or Workflow to a Concept.

```yaml
- type: references_concept
  target: CONCEPT-pressure
```

---

## `references_equation`

Connects a Paragraph to an Equation it authorizes or presents.

```yaml
- type: references_equation
  target: EQ-B313-wall-thickness
```

---

## `references_table`

Connects a Paragraph, Equation, or Lookup to a Table.

```yaml
- type: references_table
  target: TABLE-B313-allowable-stress
```

---

## `constrains_parameter`

Connects an Authority, Paragraph, Rule, or Table to a Parameter it constrains.

```yaml
- type: constrains_parameter
  target: PARAM-design-temperature
```

---

## `redirects_to`

Connects a Paragraph, Condition, or Workflow branch to an alternate path.

```yaml
- type: redirects_to
  target: B313-304.1.3
```

Example:

```text
If internal pressure branch is not applicable, redirect to external pressure branch.
```

---

# 5. Equation relationships

## `authorized_by`

Connects an Equation to the Paragraph that authorizes it.

```yaml
- type: authorized_by
  target: B313-304.1.2
```

Allowed source nodes:

```text
equation
```

Allowed target nodes:

```text
paragraph
```

---

## `requires_parameter`

Connects an Equation, Workflow, or Goal Template to required Parameters.

```yaml
- type: requires_parameter
  target: PARAM-design-pressure
```

---

## `calculates_parameter`

Connects an Equation to the Parameter it calculates.

```yaml
- type: calculates_parameter
  target: PARAM-required-wall-thickness
```

---

## `validates_parameter`

Connects a validation Equation or Rule to the Parameter it validates.

```yaml
- type: validates_parameter
  target: PARAM-thin-wall-applicability
```

---

## `depends_on_equation`

Connects one Equation to another Equation whose output is required.

```yaml
- type: depends_on_equation
  target: EQ-B313-material-allowable-stress
```

Use this only for equation-level dependency.  
If the relationship is through produced/required Parameters, prefer `requires_parameter` and `calculates_parameter`.

---

# 6. Workflow and Goal relationships

## `uses_authority`

Connects a Workflow to a normally required Authority.

```yaml
- type: uses_authority
  target: AUTH-ASME-B31.3
```

This does not activate the Authority.  
Authority Context activates it during execution.

---

## `may_use_authority`

Connects a Workflow to a possible Authority.

```yaml
- type: may_use_authority
  target: AUTH-API-570
```

---

## `starts_from_paragraph`

Connects a Workflow to a likely Paragraph entry point.

```yaml
- type: starts_from_paragraph
  target: B313-304.1.1
```

---

## `may_use_equation`

Connects a Workflow to an Equation that may participate.

```yaml
- type: may_use_equation
  target: EQ-B313-wall-thickness
```

---

## `may_create_goal`

Connects a Workflow to a Goal Template.

```yaml
- type: may_create_goal
  target: GOALTEMPLATE-required-wall-thickness
```

---

## `requires_fact`

Connects a Goal to a required Parameter or Fact.

```yaml
- type: requires_fact
  target: PARAM-design-pressure
```

Usually the Goal requires a Fact instantiating the target Parameter.

---

## `satisfied_by`

Connects a Goal to a satisfying Fact.

```yaml
- type: satisfied_by
  target: FACT-required-wall-thickness-001
```

---

## `expands_to`

Connects a parent Goal to child Goals.

```yaml
- type: expands_to
  target: GOAL-allowable-stress-001
```

---

## `blocked_by`

Connects a Goal or Execution Context to a missing Parameter, missing Fact, or failed validation.

```yaml
- type: blocked_by
  target: PARAM-design-pressure
```

---

# 7. Execution relationships

## `belongs_to_execution_context`

Connects Goals, Facts, Decisions, Events, or Validation Findings to an Execution Context.

```yaml
- type: belongs_to_execution_context
  target: EXEC-2026-000001
```

---

## `governs_execution_context`

Connects an Authority Context to the Execution Context it governs.

```yaml
- type: governs_execution_context
  target: EXEC-2026-000001
```

---

## `produced_by`

Connects a Fact to the Equation, Lookup, or execution node that produced it.

```yaml
- type: produced_by
  target: EQ-B313-wall-thickness
```

---

## `consumed_by`

Connects a Fact or Parameter to the Equation or Workflow that consumes it.

```yaml
- type: consumed_by
  target: EQ-B313-wall-thickness
```

Use cautiously. Prefer `requires_parameter` from the consumer side when possible.

---

## `recorded_event`

Connects an Execution Context to an Event.

```yaml
- type: recorded_event
  target: EVENT-calculation-completed-001
```

---

# 8. Validation relationships

## `validated_by`

Connects a Fact, Goal, or Execution Context to a validation result or rule.

```yaml
- type: validated_by
  target: RULE-B313-temperature-limit
```

---

## `requires_validation`

Connects a Workflow, Equation, or Goal to required validation.

```yaml
- type: requires_validation
  target: RULE-B313-thin-wall-limit
```

---

## `failed_because`

Connects a Goal, Fact, or Execution Context to a failed validation, missing input, or error.

```yaml
- type: failed_because
  target: VALIDATION-temperature-limit-001
```

---

## `records_override`

Connects an Authority Context or Execution Context to an override record.

```yaml
- type: records_override
  target: OVERRIDE-temperature-limit-001
```

---

# 9. Report relationships

## `included_in_report`

Connects Facts, Goals, Paragraphs, Equations, Warnings, or Decisions to a Report.

```yaml
- type: included_in_report
  target: REPORT-pipe-wall-thickness-001
```

---

## `explains`

Connects a Report section to the object it explains.

```yaml
- type: explains
  target: FACT-required-wall-thickness-001
```

---

## `supports_conclusion`

Connects a Fact, Paragraph, or Validation result to a Report conclusion.

```yaml
- type: supports_conclusion
  target: CONCLUSION-thickness-acceptable
```

---

# 10. Lifecycle relationships

## `supersedes`

Connects a newer immutable node version to an older one.

```yaml
- type: supersedes
  target: PARAM-old-pressure
```

Use for knowledge node lifecycle.

For Facts, prefer:

```yaml
supersedes_fact
```

---

## `superseded_by`

Inverse relationship.

```yaml
- type: superseded_by
  target: PARAM-new-pressure
```

---

## `deprecated_by`

Connects a deprecated node to its replacement.

```yaml
- type: deprecated_by
  target: PARAM-design-pressure
```

---

## `equivalent_to`

Connects two nodes that represent the same semantic identity.

```yaml
- type: equivalent_to
  target: PARAM-design-pressure
```

Use sparingly. Prefer one canonical node and aliases.

---

# Deprecated or discouraged relationships

Avoid these unless there is no better option:

```yaml
references
links_to
related
uses
contains
```

Replace them with more precise relationships:

|Discouraged|Prefer|
|---|---|
|`references`|`references_concept`, `references_table`, `references_equation`, `references_authority`|
|`uses`|`requires_parameter`, `uses_authority`, `may_use_equation`|
|`contains`|`contains_paragraph`, `contains_table`, `contains_rule`|
|`related`|`related_to`, only when truly weak|

---

# Directionality rules

Relationships should point from the node making the claim to the node being referenced.

Examples:

```text
Equation requires Parameter.
Paragraph introduces Parameter.
Authority contains Paragraph.
Fact instantiates Parameter.
Goal requires Fact.
Authority Context activates Authority.
```

Preferred:

```yaml
EQ-B313-wall-thickness:
  - type: requires_parameter
    target: PARAM-design-pressure
```

Not preferred:

```yaml
PARAM-design-pressure:
  - type: required_by
    target: EQ-B313-wall-thickness
```

Inverse edges may be generated by indexes.

Do not manually duplicate every inverse edge unless needed for authoring.

---

# Relationship validation rules

An edge is invalid if:

1. `type` is missing.
    
2. `target` is missing.
    
3. `type` is not in the controlled taxonomy.
    
4. Source node type is not allowed for that relationship.
    
5. Target node type is not allowed for that relationship.
    
6. The relationship meaning duplicates another stronger relationship.
    
7. The relationship is generic where a specific relationship exists.
    
8. The edge stores runtime values in immutable knowledge nodes.
    
9. The relationship creates an illegal cycle.
    
10. The relationship bypasses Authority Context for authority-governed execution.
    

---

# Conceptual rule

```text
Nodes define engineering objects.
Edges define engineering meaning between objects.
Typed relationships prevent semantic drift.
The graph should be understandable without reading prose.
```

---

# Implementation

| Artifact | Location |
|----------|----------|
| Controlled vocabulary | [`engine/reference/relationship_taxonomy.py`](../../engine/reference/relationship_taxonomy.py) — `KNOWLEDGE_EDGE_TYPES`, `RUNTIME_ONLY_EDGE_TYPES`, `RELATIONSHIP_RULES` |
| Authoring normalization | `normalize_authoring_edge()` — legacy transport → taxonomy at compile/import only |
| Query expansion | `expand_edge_types_for_query()` — traversal shims during graph DB transition |
| Validation | [`engine/reference/relationship_validator.py`](../../engine/reference/relationship_validator.py); wired from paragraph/equation/workflow validators |
| Compile | [`engine/reference/graph_compile.py`](../../engine/reference/graph_compile.py) — normalizes every `edges[]` entry before `PackGraph` storage |
| Schema | [`engine/reference/graph_edge_schema.py`](../../engine/reference/graph_edge_schema.py) — `STORED_EDGE_TYPES`, `REVERSE_ONLY_QUERY_TYPES` |
| Migration | [`scripts/migrate_relationships_to_taxonomy.py`](../../scripts/migrate_relationships_to_taxonomy.py) |
| Appendix | [`_relationship_schema.md`](_relationship_schema.md) — short on-disk edge reference |

**On-disk YAML** under `knowledge/` uses native taxonomy `type` values. Generic `references` / `requires` / `parameter` transport edges are rejected for new authoring (`allow_legacy=False` in validators).

**Runtime-only** types in this document (`instantiates`, `satisfies_goal`, `blocked_by`, `activates_authority`, report/validation edges, …) are implemented on Fact/Goal/execution models — not migrated into standards node YAML.

After changing knowledge edges, rebuild graph caches: `python scripts/build_graph_db.py` (and standards node/task DB scripts as needed).