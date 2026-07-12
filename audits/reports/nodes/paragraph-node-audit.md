# Paragraph Node YAML Audit

**Overall status:** WARN

_Filtered projection of the full node YAML audit — same findings, paragraph scope only._

## Summary

- Paragraph files inspected: 30
- Passing: 27
- Warnings: 3
- Failing: 0
- Informational findings: 8

## Enforcement policy

- Execution metadata must live under the `execution` block in primary paragraph YAML.
- `FORBIDDEN_PARAGRAPH_FRONTMATTER` keys (e.g. `trace`, `report`) → FAIL immediately.
- Registered external/unmodeled `related_to` targets → INFO.
- Policy module: `engine/reference/paragraph_authoring_policy.py`.

---

## Paragraph frontmatter inventory

| YAML file | Node ID | Validator | Result | Problems |
| --- | --- | --- | --- | --- |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.3-a.yaml` | `302.3.3-a` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.3-b.yaml` | `302.3.3-b` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.3-c.yaml` | `302.3.3-c` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-a.yaml` | `302.3.5-a` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-b.yaml` | `302.3.5-b` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-c.yaml` | `302.3.5-c` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-d.yaml` | `302.3.5-d` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-e.yaml` | `302.3.5-e` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-f.yaml` | `302.3.5-f` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-a.yaml` | `304.1.1-a` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-b.yaml` | `304.1.1-b` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.yaml` | `304.1.2-a` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-b.yaml` | `304.1.2-b` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.3.yaml` | `304.1.3` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.yaml` | `304.1` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.1-b.yaml` | `304.3.1-b` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.1-c.yaml` | `304.3.1-c` | `validate_paragraph_node` | **WARN** | unresolved related_to target: 304.7.2 — register or author node |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.1-d.yaml` | `304.3.1-d` | `validate_paragraph_node` | **WARN** | unresolved related_to target: 304.3.5 — register or author node |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.1.yaml` | `304.3.1` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 328.5.4; registered external/unmodeled reference: 300.2 |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.2-a.yaml` | `304.3.2-a` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 303 |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.2-b.yaml` | `304.3.2-b` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 328.5.4 |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.2-c.yaml` | `304.3.2-c` | `validate_paragraph_node` | **WARN** | registered external/unmodeled reference: 300.2; unresolved related_to target: 304.7.2 — register or author node |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-a.yaml` | `304.3.3-a` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 300.2; registered external/unmodeled reference: Appendix-J |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-b.yaml` | `304.3.3-b` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-c.yaml` | `304.3.3-c` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 328.5.4 |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-d.yaml` | `304.3.3-d` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-e.yaml` | `304.3.3-e` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-f.yaml` | `304.3.3-f` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.yaml` | `304.3` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.yaml` | `304` | `validate_paragraph_node` | **PASS** | — |
