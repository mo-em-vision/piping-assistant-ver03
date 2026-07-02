# Relationship schema appendix

Short reference for on-disk graph edges. Full semantics: [`Relationship Taxonomy.md`](Relationship%20Taxonomy.md).

## On-disk rule

Knowledge YAML under `knowledge/**/nodes/**/*.yaml` stores **native taxonomy** `edges[].type` values. Legacy transport types (`references`, `requires`, `parameter`, `equation`, `table`, `contains`, `constrains`, …) are accepted only at import/migration boundaries (`normalize_authoring_edge` with `allow_legacy=True`, [`scripts/migrate_relationships_to_taxonomy.py`](../../scripts/migrate_relationships_to_taxonomy.py)).

## Implementation

| Module | Role |
|--------|------|
| [`engine/reference/relationship_taxonomy.py`](../../engine/reference/relationship_taxonomy.py) | `KNOWLEDGE_EDGE_TYPES`, `LEGACY_TO_TAXONOMY` via `REFERENCE_ROLE_TO_TAXONOMY`, `normalize_authoring_edge`, `expand_edge_types_for_query` |
| [`engine/reference/relationship_validator.py`](../../engine/reference/relationship_validator.py) | Per-edge validation (`validate_edge_item`, `RELATIONSHIP_RULES`) |
| [`engine/reference/graph_edge_schema.py`](../../engine/reference/graph_edge_schema.py) | `CANONICAL_EDGE_TYPES`, `STORED_EDGE_TYPES`, `REVERSE_ONLY_QUERY_TYPES`, `REVERSE_EDGE_TYPE` |
| [`engine/reference/graph_compile.py`](../../engine/reference/graph_compile.py) | Normalizes edges before `PackGraph` compile |

Node validators call `validate_edge_item(..., allow_legacy=False)` for authoring checks.

## Knowledge edge types (stored)

Ontology: `has_concept`, `has_dimension`, `allows_unit`, `belongs_to_dimension`, `converts_to`, `property_of`, `specializes`, `generalizes`, `related_to`, `has_parameter`, `parameter_of`

Authority: `belongs_to_authority`, `contains_paragraph`, `contains_table`, `contains_rule`, `references_authority`, `refines_authority`, `conflicts_with_authority`

Paragraph / equation / workflow: `introduces_parameter`, `references_concept`, `references_equation`, `references_table`, `constrains_parameter`, `redirects_to`, `authorized_by`, `requires_parameter`, `calculates_parameter`, `validates_parameter`, `depends_on_equation`, `uses_authority`, `may_use_authority`, `starts_from_paragraph`, `may_use_equation`, `may_create_goal`

Structural / routing: `parent`, `child`, `next`, `previous`, `depends_on`, `implements`, `implemented_by`

Traceability: `introduced_by`, `introduces`, `used_by`, `consumed_by`

Lifecycle: `supersedes`, `superseded_by`, `deprecated_by`, `equivalent_to`, `alias_of`

## Reverse-only query types (do not author)

`referenced_by`, `required_by`, `contained_by`, `dependency_of`, `implemented_by`, `allowed_by`, `converted_from`, `includes_unit`, `dimension_of`, `parameter_of`, `constrained_by`

Graph indexes may expose inverses; authors store the forward taxonomy edge.

## Legacy import map (migration)

| Legacy YAML | Taxonomy |
|-------------|----------|
| `references` + `role: belongs_to_authority` | `belongs_to_authority` |
| `references` + `role: authorized_by` | `authorized_by` |
| `references` + `role: starts_from_paragraph` | `starts_from_paragraph` |
| `references` + `role: references_equation` | `references_equation` |
| `references` + `role: references_table` | `references_table` |
| `requires` | `requires_parameter` |
| `parameter` + `role: calculates` | `calculates_parameter` |
| `equation` (from paragraph) | `references_equation` |
| `equation` (from workflow) | `may_use_equation` |
| `table` / `contains` + `role: paragraph` | `contains_paragraph` |
| `contains` + `role: table` | `contains_table` |
| `constrains` | `constrains_parameter` |

Bare `references` without a resolvable `role` is rejected for new authoring.

## Runtime-only types

Fact/Goal/execution relationships (`instantiates`, `satisfies_goal`, `blocked_by`, `activates_authority`, …) live on runtime models, not immutable knowledge YAML. See **Implementation** in [`Relationship Taxonomy.md`](Relationship%20Taxonomy.md).
