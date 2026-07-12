# Designation Node Contract

## 1. Purpose

A designation node represents a named engineering classification — NPS, pipe schedule, material grade token, flange rating — that is not a physical measurable quantity.

## 2. Use this node when

- You are modeling standard nomenclature for classifications (nominal pipe size, schedule).
- A parameter with `parameter_class: material_designation` or `categorical` maps to a designation concept.
- Documentation needs a stable symbol (`NPS`, `Sch`) separate from numeric parameters.

## 3. Do not use this node when

- You need a physical measurement with units (use `parameter` + `DIM-*`).
- You need table lookup resolution (use `lookup`).
- You are starting new gatherable fields (prefer `PARAM-*` with appropriate `parameter_class`).

## 4. File location

| Form | Path |
| --- | --- |
| Template standalone | `knowledge/**/B313-designation-*.yaml` |
| Typical modern pattern | Designation semantics carried by `PARAM-*` with `parameter_class: material_designation` or `categorical` |

No standalone `type: designation` files currently exist in the repository.

## 5. ID convention

| Field | Rule |
| --- | --- |
| `id` | Template: `B313-designation-{slug}` |
| `symbol` | Standard abbreviation (`NPS`, `DN`, `Sch`) |
| `name` | Full designation name |

## 6. Copyable minimal YAML skeleton

```yaml
---
id: B313-designation-nps
type: designation
name: Nominal Pipe Size
symbol: NPS
description: >
  Pipe size designation per ASME B36.10 — not a physical quantity.
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Unique identity |
| `type` | `designation` |
| `name` | Human-readable name |
| `symbol` | Standard abbreviation |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `description` | Engineering definition |
| `aliases` | Alternate abbreviations |
| `edges` | Link to related `PARAM-*` nodes |

## 9. Forbidden fields

```text
value, user_input, runtime_value, fact_value, dimension,
unit, resolution, execution_id
```

Designations must not carry `dimension` — they are not physical quantities.

Also forbidden:

- Top-level `links` block

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `has_parameter` | `PARAM-*` | From concept-like grouping |
| `related_to` | designation / concept | Semantic association |
| Legacy `references` | parameter | Migration only |

Parameters collect runtime selections; designations define the classification meaning.

## 11. Fields consumed by runtime components

Parameters with `parameter_class: categorical` or `material_designation` store runtime label tokens as Facts. Lookup tables may use designation parameters as row keys. Designation nodes themselves are primarily documentary in the current codebase.

## 12. Validation procedure

No dedicated validator. Validate manually:

1. Confirm `type: designation` and required `symbol`.
2. Confirm no `dimension` or runtime value fields.
3. Confirm linked `PARAM-*` exists when referenced.
4. Prefer `PARAM-nominal-pipe-size` pattern for active gatherable fields.

## 13. Common authoring mistakes

- Adding `dimension` to a designation node.
- Storing user selections (`Sch 40`) on the designation node.
- Creating designation nodes without corresponding `PARAM-*` gatherable fields.
- Confusing outside diameter (physical quantity) with NPS (designation).
- Omitting revision metadata.

## 14. Current repository examples

Template only:

- Former template example id: `B313-designation-nps`

Related parameter nodes carrying designation semantics:

- `knowledge/global/parameters/nodes/PARAM-nominal-pipe-size.yaml`
- `knowledge/global/parameters/nodes/PARAM-pipe-schedule.yaml`
- `knowledge/global/parameters/nodes/PARAM-material-grade.yaml`

## 15. Implementation evidence appendix

- Validator: none dedicated; ontology patterns from `tests/reference/test_knowledge_node_links.py`
- Parameter classes: `engine/validation/parameter_node_validator.py` — `material_designation`, `categorical` in `ALLOWED_PARAMETER_CLASSES`
- Dimension for designations: `knowledge/global/dimensions/nodes/DIM-material-designation.yaml`
