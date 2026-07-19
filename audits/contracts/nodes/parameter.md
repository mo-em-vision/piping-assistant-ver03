# Parameter Node Contract

## 1. Purpose

A parameter node defines a reusable engineering field — its semantic meaning, class, dimension, and where it is introduced — without storing runtime values or resolution outcomes.

## 2. Use this node when

- You need a canonical gatherable field for workflows (pressure, diameter, material grade).
- You are binding symbols in equations, lookups, or validation rules.
- You need composer and messaging metadata for user prompts.

## 3. Do not use this node when

- You only need a broad semantic grouping (use `concept`).
- You need to store the user's entered value (runtime Fact).
- You need a physical quantity node without task binding (legacy `quantity` — prefer parameter).
- You need a table or formula (use `lookup` or `equation`).

## 4. File location

`knowledge/global/parameters/nodes/PARAM-{slug}.yaml`

Pack-local parameters are discouraged; prefer global `PARAM-*` nodes referenced from standards content.

## ID convention

| Field | Rule |
| --- | --- |
| `id` | `PARAM-{kebab-case-slug}` derived from `name` (lowercase words, hyphen-separated) |
| `key` | Underscore form of the id slug: `PARAM-{slug}` → `{slug_with_underscores}` |
| `name` | Title Case human label; must match the words in the id slug |
| `introduced_by` | Pack-qualified paragraph ids (`asme-b313-304-1-1-b`) |

Derive slugs with `param_id_from_name()` / `param_key_from_param_id()` in
`engine/reference/parameter_keys.py`. The validator rejects `id`/`key` pairs that
do not match `name`.

## 6. Copyable minimal YAML skeleton

```yaml
---
id: PARAM-example-field
type: parameter
key: example_field
name: Example Field
parameter_class: physical_quantity
description: >
  Stable semantic definition of the example engineering field.
introduced_by:
  - asme-b313-304-1-1-b
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Starts with `PARAM-` |
| `type` | `parameter` |
| `key` | Machine key |
| `name` | Human-readable name |
| `parameter_class` | One of allowed classes (see section 8) |
| `description` | Non-empty definition |
| `introduced_by` | Non-empty list of pack-qualified paragraph ids (top-level, not edges) |
| `metadata.last_revision` | ISO date |
| `metadata.edited_by` | Author |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `dimension` | `DIM-*` reference |
| `canonical_symbol` | Symbol in equations (e.g. `S`) |
| `aliases` | Search synonyms |
| `user_prompt.prompt` | Brief composer heading |
| `user_prompt.help_text` | Optional engineering guidance (not unit-entry instructions) |
| `metadata.composer_input` | UI control type |
| `metadata.composer_options` | Static dropdown choices (ordinary value collection; not decision copy when `execution.interactions` owns the decision) |
| `metadata.resolution_branch_question` | Branch-selection question for `resolution_branch` parameters |
| `metadata.resolution_branch_help_text` | Optional prompt-level help for branch selection |
| `metadata.resolution_branches` | Resolution path definitions (see below) |
| `metadata.canonical_unit` | Default unit symbol or `UNIT-*` |
| `metadata.default_value` | Proposed default |
| `metadata.input_examples` | Prompt examples |
| `metadata.prompt_use_description` | Skip description in prompts when `false` |
| `metadata.role` | Parameter runtime role (`path_decision` for branch-driving categorical fields) |
| `metadata.status` | Lifecycle |
| `edges` | `has_dimension`, `used_by`, etc. |

### `metadata.resolution_branches` schema

For parameters with `metadata.composer_input: resolution_branch`:

| Field | Rule |
| --- | --- |
| `metadata.resolution_branch_question` | Composer question for branch selection |
| `metadata.resolution_branch_help_text` | Optional prompt-level help |
| `resolution_branches[].id` | Branch fact value |
| `resolution_branches[].label` | Composer tab/option label |
| `resolution_branches[].help_text` | Optional per-branch help |
| `resolution_branches[].report_statement` | **Required** report-ready prose; same placeholders as paragraph interactions |
| `resolution_branches[].method` | `table_lookup` or `user_input` |
| `resolution_branches[].via_parameters` | Prerequisite PARAM ids for lookup branches |

`user_prompt` on resolution-branch parameters is for **post-branch value entry** (e.g. direct numeric OD), not the branch-selection question.


```text
physical_quantity, geometric_quantity, material_designation,
coefficient, factor, categorical, environmental_condition,
calculated_quantity, selection
```

## 9. Forbidden fields

```text
value, unit, resolution, source, timestamp,
execution_id, workflow_id, status (top-level)
```

Also forbidden:

- `introduced_by` as an edge type (must be top-level list)
- Top-level `links` block
- Legacy paragraph refs (`B313-*`, `asme_b313_*` without `asme-b313-` qualification)
- Legacy prompt fields `question`, `short_question`, `metadata.question`, and `metadata.short_question` (use top-level `user_prompt`)

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `has_dimension` | `DIM-*` | Unit compatibility |
| `used_by` | equation, lookup, paragraph, table id | Traceability |
| `has_concept` | `CONCEPT-*` | Optional semantic parent |
| Other taxonomy edges | per `relationship_validator` | Validated per edge |

Do **not** author `introduced_by` in `edges` — compiler emits those from the top-level list.

## 11. Fields consumed by runtime components

Graph expansion activates parameters on the expanded path and reads `applicability` on related nodes. Planner selects the next missing parameter from active graph nodes. Messaging reads `user_prompt`, `description`, and composer metadata for prompts. Execution binds `requires`/`returns` entries to `PARAM-*` ids via Facts. Desktop composer reads structured `prompt` / `help_text` from API payloads plus `metadata.composer_input` and `metadata.composer_options`.

## 12. Validation procedure

1. Parse YAML frontmatter.
2. Run `validate_parameter_node(meta)` from `engine/validation/parameter_node_validator.py`.
3. Confirm each `introduced_by` entry uses pack-qualified ids.
4. Confirm `parameter_class` is in `ALLOWED_PARAMETER_CLASSES`.
5. Run `python -m pytest tests/reference -k parameter -q` when changing global parameters.

## 13. Common authoring mistakes

- Putting `introduced_by` in `edges` instead of top-level list.
- Using bare paragraph numbers (`304.1.1-b`) without pack prefix in `introduced_by`.
- Storing runtime `value` or `resolution` on the node.
- Omitting `user_prompt.prompt` for gatherable parameters (falls back to thin descriptions).
- Using `categorical` / `selection` on concept nodes instead of parameters.

## 14. Current repository examples

- `knowledge/global/parameters/nodes/PARAM-allowable-stress.yaml`
- `knowledge/global/parameters/nodes/PARAM-internal-design-gage-pressure.yaml`
- `knowledge/global/parameters/nodes/PARAM-pressure-design-case.yaml`
- `knowledge/global/parameters/nodes/PARAM-basic-casting-quality-factor.yaml`
- `knowledge/global/parameters/nodes/PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/parameter_node_validator.py` — `validate_parameter_node`, `ALLOWED_PARAMETER_CLASSES`, `_FORBIDDEN_FIELDS`
- Qualification: `engine/reference/asme_b313_node_ids.py` — `is_qualified_paragraph_ref`, `qualify_cross_pack_ref`
- Prompt context: `engine/messaging/parameter_prompt_context.py`
- Metadata helpers: `engine/reference/parameter_metadata.py`
