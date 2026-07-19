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

One primary YAML file per paragraph. Node-owned execution metadata lives in the nested `execution` block in that file (not in separate sidecar files).

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
execution:
  applicability:
    applies_when: []
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
| `execution` | Applicability, assumptions, interactions, conditions, subsections, parameter_defaults |
| `nomenclature` | Optional symbol table; prefer `introduces_parameter` edges |

### `execution.interactions` decision schema

Each decision interaction on a condition-owning paragraph must declare:

| Field | Rule |
| --- | --- |
| `id` | Stable interaction id (machine key) |
| `parameter` or `field` | Bound `PARAM-*` id or fact key |
| `question` | Composer question text |
| `help_text` | Optional prompt-level help (tooltip only) |
| `options` | Non-empty list of selectable outcomes |
| `options[].value` | Stored fact value |
| `options[].label` | Composer option label |
| `options[].help_text` | Optional per-option help (tooltip only) |
| `options[].report_statement` | **Required** report-ready prose after selection; supports `{selected_label}`, `{requesting_reference}`, `{activated_reference}` only |

`execution.assumptions` remains for graph expansion gating only — not a presentation copy source when `execution.interactions` is authored for the same field.

Do **not** set `text.source_language` — inherited from `pack.yaml`.

## 9. Forbidden fields

Field placement is enforced by `engine/reference/paragraph_authoring_policy.py`:

| Category | Severity | Meaning |
| --- | --- | --- |
| `FORBIDDEN_RUNTIME_STATE_KEYS` | FAIL | Task/runtime mutable state — never in knowledge YAML |
| `FORBIDDEN_PARAGRAPH_FRONTMATTER` | FAIL | Legacy/wrong-layer fields — use edges or `execution` block |
| `EXECUTION_BLOCK_KEYS` at top level | FAIL | Belong in nested `execution` block in primary YAML |

Hard-fail top-level keys include execution metadata such as `assumptions`, `applicability`, `conditions`, and `parameter_defaults` — place them under `execution:`.

Also forbidden:

- `hierarchy.previous` / `hierarchy.next`
- Top-level `links` block
- Structural edges (`parent`, `child`, `next`, `previous`) in `edges`
- Node-owned sidecar files (`{id}.execution.yaml`, `{id}.nomenclature.yaml`)

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

**Canonical authoring:** Graph expansion, assumption checking, and interaction resolution read `execution.applicability`, `execution.assumptions`, and `execution.interactions` from the nested `execution` block in the primary paragraph YAML.

**Legacy runtime compatibility (read-only):** `engine/reference/paragraph_sidecar.py` may still merge metadata from old `{id}.execution.yaml` files when present during pack load. This loader path is migration compatibility only — do not author, create, or maintain execution sidecars. Consolidate any remaining legacy files into the primary YAML `execution:` block.

Flow guidance uses `text.original` and `presentation` for paragraph blocks. Parameter introduction traces use `introduces_parameter` edges on the primary YAML. Do not create separate nomenclature sidecar files (`{id}.nomenclature.yaml`; §9). Optional inline `nomenclature` on the primary file when used (§8). Hierarchy metadata drives section navigation in standards browsers.

## 12. Validation procedure

1. Parse YAML frontmatter.
2. Run `validate_paragraph_node(meta)` from `engine/validation/paragraph_node_validator.py`.
3. Run `check_paragraph_frontmatter_placement(meta)` from `engine/reference/paragraph_authoring_policy.py` for WARN-level placement debt when execution keys appear outside the nested `execution` block.
4. Confirm `authority` is a known `AUTH-*` value.
5. For nomenclature paragraphs, confirm edge types are restricted.
6. If legacy `{id}.execution.yaml` files remain on disk, treat them as migration debt: consolidate into the primary YAML `execution:` block and confirm no duplicate or split authoring surfaces.
7. Rebuild pack graph: `python scripts/build_graph_db.py`.
8. Run paragraph audit: `python scripts/audit_current_node_yaml.py --filter paragraph`.

**Enforcement policy (phase 1):** `assumptions` and `parameter_defaults` in frontmatter emit WARN (migration required), not validator FAIL. `applicability` in frontmatter remains FAIL. Phase 2 promotes misplaced execution-block keys to FAIL when `EXECUTION_BLOCK_ENFORCEMENT = "fail"` in the policy module and all known violations are migrated.

## 13. Common authoring mistakes

- Using `304.1.2(a)` in `paragraph_number` instead of `304.1.2-a`.
- Inventing `304.3.1-a` when the standard has no subsection (a).
- Creating or retaining a separate `{id}.execution.yaml` file instead of nesting `applicability`, `interactions`, and related keys under `execution:` in the primary YAML.
- Putting `applicability` or `interactions` at top level instead of under nested `execution:`.
- Using `related_to` for parent/child structure.
- Setting `text.source_language` on the node instead of `pack.yaml`.
- Adding `references_*` edges on nomenclature paragraphs.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-b.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.yaml`

## 15. Implementation evidence appendix

- Policy: `engine/reference/paragraph_authoring_policy.py` — placement categories, `check_paragraph_frontmatter_placement`, `classify_edge_target`, `EXTERNAL_UNMODELED_REF_REGISTRY`
- Validator: `engine/validation/paragraph_node_validator.py` — `validate_paragraph_node`, `validator_fail_messages_for_frontmatter`
- Legacy sidecar merge (read-only at load): `engine/reference/paragraph_sidecar.py` — `merge_paragraph_sidecar_metadata` may read old `{id}.execution.yaml` files; not an authoring surface
- Structural edges: `engine/validation/structural_edges.py` — `validate_no_structural_edges`
- Revision: `engine/validation/node_revision_metadata.py` — `validate_revision_metadata`
