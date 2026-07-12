# Paragraph Node Contract

## 1. Purpose

A paragraph node stores the exact authoritative text of one subdivision of a standard (or similar source) and links that text to related engineering objects via typed graph edges.

## 2. Use this node when

- You are capturing official prose from a governing document (ASME, ASTM, company spec).
- You need a stable anchor for equations, lookups, parameters, or cross-paragraph citations.
- You are modeling lettered subsections as separate nodes (`304.1.2-a`, not `304.1.2` + subsection field).

## 3. Do not use this node when

- You need to store a formula (use `equation`).
- You need table resolution logic (use `lookup`).
- You need pass/fail checks (use `validation_rule`).
- You need runtime branch state, user values, or calculation results.

## 4. File location

`knowledge/standards/<publisher>/<pack>/nodes/paragraph/{id}.yaml`

Optional sidecars (same directory):

- `{id}.execution.yaml` or `{id}/execution.yaml`
- `{id}.nomenclature.yaml` or `{id}/nomenclature.yaml`

## 5. ID convention

| Case | Rule | Example |
| --- | --- | --- |
| Lettered subsection | `{section}-{lowercase_letter}` | `304.1.2-a` |
| Unlettered paragraph | Bare section id | `304.1.3` |
| Preamble before (b) | Unsuffixed base id | `304.3.1` with children `304.3.1-b` |
| `paragraph_number` | Must equal `id` (hyphen form, not parentheses) | `304.1.2-a` not `304.1.2(a)` |
| `key` | Underscore machine key | `b313_304_1_2_a` |
| Pack prefix | Bare ids within pack (no `B313-` on paragraph ids) | `304.1.1-a` |

## 6. Copyable minimal YAML skeleton

```yaml
---
id: 304.1.2-a
type: paragraph
key: b313_304_1_2_a
title: Example Paragraph Title
authority: AUTH-ASME-B31.3
edition: 2024
paragraph_number: 304.1.2-a
text:
  original: >
    Exact original paragraph text from the standard.
hierarchy:
  parent: '304.1'
  children: []
edges:
  - type: belongs_to_authority
    target: AUTH-ASME-B31.3
metadata:
  source_revision_year: 2024
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Equals filename; equals `paragraph_number`. |
| `type` | `paragraph` |
| `key` | Machine key |
| `title` | Human-readable heading |
| `authority` | `AUTH-*` id (known authorities validated) |
| `edition` | Edition year or label |
| `paragraph_number` | Same as `id` |
| `text.original` | Non-empty original prose |
| `hierarchy.parent` | Parent section id |
| `hierarchy.children` | Ordered list (use `[]` for leaves) |
| `metadata.source_revision_year` | Source revision year |
| `metadata.last_revision` | ISO date |
| `metadata.edited_by` | Author |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `presentation.summary` | Center-panel scroll summary |
| `presentation.display_label` | Heading override |
| `presentation.reference_label` | Chip label override |
| `metadata.kind` | `nomenclature` for nomenclature-only paragraphs |
| `metadata.status` | Lifecycle status |
| `metadata.node_version` | Version counter |
| `edges` | References to concepts, equations, tables, parameters, etc. |
| Sidecar files | Execution, nomenclature — see sidecar contracts |

Do **not** set `text.source_language` — inherited from `pack.yaml`.

## 9. Forbidden fields

```text
runtime_value, fact_value, user_input, execution_id, task_id,
calculation_result, selected_for_execution, active_in_context,
paragraph_class, applicability, limitations, exceptions,
calculation_logic, validation_logic, introduced_parameters,
referenced_equations, referenced_concepts, referenced_validation_rules,
engineering_intent, text.source_language
```

Also forbidden:

- `hierarchy.previous` / `hierarchy.next`
- Top-level `links` block
- Structural edges (`parent`, `child`, `next`, `previous`) in `edges`
- Execution keys in frontmatter when a sidecar is used (prefer sidecar)

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `belongs_to_authority` | `AUTH-*` | Required membership |
| `references_concept` | `CONCEPT-*` | Semantic linkage |
| `references_parameter` | `PARAM-*` | Citation in prose |
| `references_equation` | `asme-b313-*` / `EQ-*` | May include `when` conditions |
| `references_lookup` | lookup id | Table resolution reference |
| `references_table` | table / lookup id | Tabular data reference |
| `references_validation_rule` | validation rule id | Rule citation |
| `related_to` | paragraph id | Cross-paragraph citation only |
| `introduces_parameter` | `PARAM-*` | Nomenclature paragraphs only |

Nomenclature paragraphs (`metadata.kind: nomenclature` or only `introduces_parameter` edges) may use only `belongs_to_authority` and `introduces_parameter`.

## 11. Fields consumed by runtime components

Graph expansion reads sidecar `applicability`, `assumptions`, and `interactions` merged from execution sidecars. Flow guidance uses `text.original` and `presentation` for paragraph blocks. Parameter introduction traces use `introduces_parameter` edges and nomenclature sidecars. Hierarchy metadata drives section navigation in standards browsers.

## 12. Validation procedure

1. Parse YAML frontmatter.
2. Run `validate_paragraph_node(meta)` from `engine/validation/paragraph_node_validator.py`.
3. Confirm `authority` is a known `AUTH-*` value.
4. For nomenclature paragraphs, confirm edge types are restricted.
5. If sidecars exist, validate against sidecar contracts.
6. Rebuild pack graph: `python scripts/build_graph_db.py`.

## 13. Common authoring mistakes

- Using `304.1.2(a)` in `paragraph_number` instead of `304.1.2-a`.
- Inventing `304.3.1-a` when the standard has no subsection (a).
- Putting `applicability` or `interactions` in frontmatter instead of `.execution.yaml`.
- Using `related_to` for parent/child structure.
- Setting `text.source_language` on the node instead of `pack.yaml`.
- Adding `references_*` edges on nomenclature paragraphs.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-b.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.execution.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/paragraph_node_validator.py` — `validate_paragraph_node`, `_KNOWN_AUTHORITIES`, `_FORBIDDEN_FIELDS`, `_NOMENCLATURE_FORBIDDEN_EDGE_TYPES`
- Sidecar merge: `engine/reference/paragraph_sidecar.py` — `merge_paragraph_sidecar_metadata`, `_EXECUTION_KEYS`
- Structural edges: `engine/validation/structural_edges.py` — `validate_no_structural_edges`
- Revision: `engine/validation/node_revision_metadata.py` — `validate_revision_metadata`
