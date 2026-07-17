# Workflow Node YAML Audit

**Overall status:** WARN

_Filtered projection aligned with `audits/contracts/nodes/workflow.md` (legacy separate runtime files are audited for presence only; nested `runtime` in primary YAML is canonical)._

## Summary

- Workflow primary files inspected: 2
- Legacy workflow runtime files inspected: 0
- Passing: 0
- Warnings: 2
- Failing: 0

## Enforcement policy

- Validator: `engine/validation/workflow_node_validator.py`.
- Placement: runtime keys must live under nested `runtime` block (`workflow_authoring_policy`).
- Filename convention: `workflows/{machine-key}.yaml` (stem may differ from `WF-*` id).
- Supplementary tests: `tests/reference/test_workflow_ontology.py`.

---

## Workflow primary YAML inventory

| YAML file | Node ID | Validator | Result | Problems |
| --- | --- | --- | --- | --- |
| `workflows/mawp.yaml` | `WF-MAWP` | `validate_workflow_node` | **WARN** | filename stem 'mawp' differs from id 'WF-MAWP' |
| `workflows/pipe-wall-thickness.yaml` | `WF-PIPE-WALL-THICKNESS` | `validate_workflow_node` | **WARN** | filename stem 'pipe-wall-thickness' differs from id 'WF-PIPE-WALL-THICKNESS' |

## Legacy workflow runtime file inventory

| YAML file | Parent workflow | Contract | Result | Problems |
| --- | --- | --- | --- | --- |
| _none_ | — | — | **PASS** | Runtime metadata uses nested `runtime` block in primary YAML |
