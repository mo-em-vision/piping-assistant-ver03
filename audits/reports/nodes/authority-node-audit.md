# Authority Node YAML Audit

**Overall status:** PASS

_Filtered projection aligned with `audits/contracts/nodes/authority.md`._

## Summary

- Authority files inspected: 3
- Passing: 3
- Warnings: 0
- Failing: 0

## Enforcement policy

- Validator: `engine/validation/authority_node_validator.py`.
- Required: `AUTH-*` id, `key`, `name`, `authority_class`, `description`, revision metadata.
- Forbidden: runtime activation/value fields and top-level `links`.
- Edge targets resolved against repository index (`classify_edge_target`).
- Supplementary tests: `tests/reference/test_authority_ontology.py`.

---

## Authority node inventory

| YAML file | Node ID | Validator | Result | Problems |
| --- | --- | --- | --- | --- |
| `knowledge/global/authorities/nodes/AUTH-ASME-B31.3.yaml` | `AUTH-ASME-B31.3` | `validate_authority_node` | **PASS** | — |
| `knowledge/global/authorities/nodes/AUTH-ASME-B36.10M.yaml` | `AUTH-ASME-B36.10M` | `validate_authority_node` | **PASS** | — |
| `knowledge/global/authorities/nodes/AUTH-ASTM-A106.yaml` | `AUTH-ASTM-A106` | `validate_authority_node` | **PASS** | — |
