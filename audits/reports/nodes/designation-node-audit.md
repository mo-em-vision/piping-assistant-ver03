# Designation Node YAML Audit

**Overall status:** PASS

_Filtered projection aligned with `audits/contracts/nodes/designation.md`._

## Summary

- Designation files inspected: 0
- Passing: 0
- Warnings: 0
- Failing: 0

## Enforcement policy

- Validator: `engine/validation/designation_node_validator.py`.
- Required: `name`, `symbol`; forbidden: `dimension`, runtime value fields.
- Active gatherable designation semantics live on `PARAM-*` nodes per contract.

---

## Designation node inventory

| YAML file | Node ID | Validator | Result | Problems |
| --- | --- | --- | --- | --- |
| _none_ | — | — | **PASS** | No `type: designation` nodes authored yet |

## Related parameter nodes (designation semantics)

No standalone designation YAML is required when parameters carry designation semantics — see `PARAM-nominal-pipe-size`, `PARAM-pipe-schedule`, `PARAM-material-grade`.

