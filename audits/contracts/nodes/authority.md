# Authority Node Contract

## 1. Purpose

An authority node defines a canonical governing engineering source — a design code, material standard, regulation, or company specification — as immutable graph knowledge.

## 2. Use this node when

- You are registering ASME B31.3, ASTM A106, or similar standards in the global authority ontology.
- Paragraphs, tables, equations, and lookups need an `AUTH-*` anchor.
- Authority Context at runtime will select which authorities are active for a task.

## 3. Do not use this node when

- You need paragraph text (use `paragraph` with `authority: AUTH-*`).
- You need to mark which authority is active for the current task (Authority Context runtime model).
- You need company-project-specific overrides without a stable global identity.

## 4. File location

`knowledge/global/authorities/nodes/AUTH-{STANDARD}.yaml`

## 5. ID convention

| Field | Rule |
| --- | --- |
| `id` | `AUTH-{PUBLISHER}-{STANDARD}` (e.g. `AUTH-ASME-B31.3`) |
| `key` | Underscore machine key (`asme_b31_3`) |
| `authority_class` | From allowed list (section 8) |

## 6. Copyable minimal YAML skeleton

```yaml
---
id: AUTH-EXAMPLE
type: authority
key: example_standard
name: Example Standard
authority_class: design_code
description: >
  Example governing engineering standard for illustration.
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Starts with `AUTH-` |
| `type` | `authority` |
| `key` | Machine key |
| `name` | Short standard name |
| `authority_class` | Allowed class (section 8) |
| `description` | Non-empty |
| `metadata.last_revision`, `metadata.edited_by` | Revision metadata |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `publisher` | Issuing body (ASME, ASTM) |
| `title` | Full document title |
| `editions` | Year, status, effective dates |
| `scope.domain`, `scope.equipment`, `scope.lifecycle_phase` | Applicability metadata |
| `contains.paragraphs`, `contains.tables` | Inventory lists |
| `edges` | `contains_paragraph`, `contains_table` |
| `metadata.status` | Lifecycle |

### Allowed `authority_class` values

```text
design_code, inspection_code, material_standard, dimensional_standard,
testing_standard, regulation, company_standard, project_specification,
client_requirement, reference_standard, recommended_practice,
engineering_procedure, manufacturer_document
```

## 9. Forbidden fields

```text
runtime_value, fact_value, execution_id, task_id,
selected_for_execution, active_in_context, calculation_result,
user_input, value, unit, source, timestamp
```

Also forbidden:

- Top-level `links` block
- Runtime active/inactive flags (Authority Context owns activation)

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `contains_paragraph` | paragraph id | Standard content inventory |
| `contains_table` | table / lookup id | Tabular content |
| `contains_rule` | validation rule id | Rule inventory |
| `constrains_parameter` | `PARAM-*` | Parameters governed by this standard (e.g. NPS, schedule, OD, thickness) |
| `references_authority` | `AUTH-*` | Cross-standard reference |
| `refines_authority` | `AUTH-*` | Narrower scope |
| `conflicts_with_authority` | `AUTH-*` | Documented conflicts |

Paragraphs link back via `belongs_to_authority`.

## 11. Fields consumed by runtime components

Authority Context stores `active_authorities[].authority_id` referencing `AUTH-*` nodes. Paragraph validators check `authority` field against known authorities. Graph expansion may gate content on active authority set. Workflow `expected_authorities` lists compatible authorities for a task type.

## 12. Validation procedure

Dedicated validator: `engine/validation/authority_node_validator.py`.

Audit projection:

```bash
python scripts/audit_current_node_yaml.py --filter authority
```

Report: `audits/reports/nodes/authority-node-audit.md`.

Checks:

1. Parse YAML frontmatter.
2. Run `validate_authority_node(meta)`.
3. Confirm `authority_class` in `ALLOWED_AUTHORITY_CLASSES`.
4. Confirm typed `edges` and that contained paragraph/table targets exist in the repository index.
5. Run `tests/reference/test_authority_ontology.py` and `tests/reference/test_authority_audit_process.py`.

## 13. Common authoring mistakes

- Using non-`AUTH-` prefixed ids.
- Unknown `authority_class` strings.
- Storing runtime activation on the authority node.
- Referencing authorities from paragraphs with unofficial string labels instead of `AUTH-*` ids.
- Omitting revision metadata on edits.

## 14. Current repository examples

- `knowledge/global/authorities/nodes/AUTH-ASME-B31.3.yaml`
- `knowledge/global/authorities/nodes/AUTH-ASME-B36.10M.yaml`
- `knowledge/global/authorities/nodes/AUTH-ASTM-A106.yaml`

## 15. Implementation evidence appendix

- Validator: `engine/validation/authority_node_validator.py` — `validate_authority_node`, `ALLOWED_AUTHORITY_CLASSES`; audit `--filter authority` → `audits/reports/nodes/authority-node-audit.md`
- Tests: `tests/reference/test_authority_ontology.py`, `tests/reference/test_authority_audit_process.py`
