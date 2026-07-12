# Validation Rule Node YAML Audit

**Overall status:** WARN

_Filtered projection aligned with `audits/contracts/nodes/validation-rule.md`._

## Summary

- Validation rule primary files inspected: 4
- Validation rule sidecar files inspected: 0
- Passing: 1
- Warnings: 3
- Failing: 0

## Enforcement policy

- Validator: `engine/validation/validation_rule_node_validator.py`.
- Authority: `validate_authority_authorization` on `authority.authorized_by`.
- Required: `validates` list or `validates_parameter` edge; `rule_class: validation`.
- Forbidden: `calculates_parameter` edges, structural edges, runtime value fields.
- Edge targets resolved against repository index; missing PARAM targets surface as WARN.
- Supplementary tests: `tests/reference/test_validation_rule_ontology.py`.

---

## Validation rule primary YAML inventory

| YAML file | Node ID | Validator | Result | Problems |
| --- | --- | --- | --- | --- |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-1-valrule-a.yaml` | `asme-b313-304-1-1-valrule-a` | `validate_validation_rule_node` | **WARN** | edge target not in repository index: PARAM-wall-thickness-adequacy |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-2-valrule-a.yaml` | `asme-b313-304-1-2-valrule-a` | `validate_validation_rule_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-2-valrule-b.yaml` | `asme-b313-304-1-2-valrule-b` | `validate_validation_rule_node` | **WARN** | edge target not in repository index: PARAM-thick-wall-special-consideration-required |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-3-3-valrule-6a.yaml` | `asme-b313-304-3-3-valrule-6a` | `validate_validation_rule_node` | **WARN** | edge target not in repository index: PARAM-reinforcement-adequate |
