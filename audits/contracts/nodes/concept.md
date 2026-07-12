# Concept Node Contract

## 1. Purpose

A concept node defines a reusable semantic engineering idea broader than any single parameter — grouping related `PARAM-*` nodes under one ontology entry.

## 2. Use this node when

- Several parameters represent roles of the same idea (design pressure, operating pressure, MAWP under `CONCEPT-pressure`).
- Paragraphs reference engineering ideas without binding a specific parameter role.
- You need ontology classification (`physical_quantity`, `material`, `selection`).

## 3. Do not use this node when

- You need a gatherable workflow field (use `parameter`).
- You need `selection` or `categorical` runtime UI behavior (those belong on `parameter.parameter_class`).
- You need a governing standard document (use `authority`).

## 4. File location

`knowledge/global/concepts/nodes/CONCEPT-{slug}.yaml`

## 5. ID convention

| Field | Rule |
| --- | --- |
| `id` | `CONCEPT-{kebab-case}` |
| `key` | Underscore machine key |
| `concept_class` | From allowed list (section 8) |
| Forbidden classes | `category`, `categorical` |

## 6. Copyable minimal YAML skeleton

```yaml
---
id: CONCEPT-pressure
type: concept
key: pressure
name: Pressure
concept_class: physical_quantity
description: >
  The engineering concept of pressure as force per unit area.
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Starts with `CONCEPT-` |
| `type` | `concept` |
| `key` | Machine key |
| `name` | Human-readable name |
| `concept_class` | Valid class from section 8 |
| `description` | Non-empty definition |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `dimension` | `DIM-*` for physical/geometric concepts |
| `aliases` | Synonyms |
| `edges` | `has_dimension`, `has_parameter`, `specializes` |
| `metadata.status` | Lifecycle |

### Allowed `concept_class` values

```text
physical_quantity, geometric_quantity, material, fluid, component,
condition, coefficient, factor, selection, failure_mode,
inspection_method, authority_concept
```

### Forbidden `concept_class` values

```text
category, categorical
```

Physical/geometric concepts should declare `dimension` and `has_dimension` edge.

## 9. Forbidden fields

```text
value, unit, source, timestamp, execution_id, workflow_id, project_id,
resolution, formula, calculation_result
```

Also forbidden:

- `concept_class: category` or `categorical`
- Top-level `links` block
- Composer / prompt metadata (belongs on parameters)

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `has_dimension` | `DIM-*` | Physical concepts |
| `has_parameter` | `PARAM-*` | Grouped parameters |
| `specializes` | `CONCEPT-*` | Ontology hierarchy |
| `generalizes` | `CONCEPT-*` | Inverse specialization |
| `related_to` | concept / paragraph | Loose association |

Paragraphs reference concepts via `references_concept` edges (incoming).

## 11. Fields consumed by runtime components

Graph compilation indexes concept-parameter groupings for traceability and search. Workflow `applicability.applies_to` may filter on `CONCEPT-*` ids. Paragraph presentation may surface related concepts. Concepts do not directly drive parameter prompts or execution.

## 12. Validation procedure

Dedicated validator: `engine/validation/concept_node_validator.py`

Audit projection:

```bash
python scripts/audit_current_node_yaml.py --filter concept
```

Reports: `audits/reports/nodes/concept-node-audit.md` (concept projection) and `audits/reports/nodes/current-node-yaml-audit.md` (full run).

Tests: `tests/reference/test_concept_ontology.py`, `tests/reference/test_concept_audit_process.py`

## 13. Common authoring mistakes

- Putting `selection` / `categorical` behavior on concepts instead of parameters.
- Using `concept_class: category` (forbidden).
- Omitting `has_parameter` edges when parameters clearly belong to the concept.
- Storing runtime values on concept nodes.
- Duplicating parameter definitions inside concept description instead of linking `PARAM-*`.

## 14. Current repository examples

- `knowledge/global/concepts/nodes/CONCEPT-pressure.yaml`
- `knowledge/global/concepts/nodes/CONCEPT-material.yaml`
- `knowledge/global/concepts/nodes/CONCEPT-wall-thickness.yaml`
- `knowledge/global/concepts/nodes/CONCEPT-weld-joint-efficiency.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/concept_node_validator.py`
- Tests: `tests/reference/test_concept_ontology.py`, `tests/reference/test_concept_audit_process.py`
- Revision: `engine/validation/node_revision_metadata.py` — `validate_revision_metadata`
- Edge targets: `engine/reference/graph_edge_schema.py` — `edge_targets`
- Ontology tests: `tests/reference/test_concept_ontology.py`
