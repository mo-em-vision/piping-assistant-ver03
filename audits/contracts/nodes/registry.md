# Node Contract Registry

Authoritative index of YAML authoring contracts under `audits/contracts/nodes/`. Human-readable authoring source; **enforcement authority** is `engine/validation/*_node_validator.py` and ontology tests — not these Markdown contracts.

Start here: [00-START-HERE.md](00-START-HERE.md). Shared rules: [01-shared-node-contract.md](01-shared-node-contract.md).

## Node type contracts

| Contract | Node `type` |
| --- | --- |
| [paragraph.md](paragraph.md) | `paragraph` |
| [parameter.md](parameter.md) | `parameter` |
| [equation.md](equation.md) | `equation` |
| [lookup.md](lookup.md) | `lookup` |
| [validation-rule.md](validation-rule.md) | `validation_rule` |
| [workflow.md](workflow.md) | `workflow` |
| [table.md](table.md) | `table` |
| [table-note.md](table-note.md) | `table_note` |
| [unit.md](unit.md) | `unit` |
| [dimension.md](dimension.md) | `dimension` |
| [concept.md](concept.md) | `concept` |
| [authority.md](authority.md) | `authority` |
| [text.md](text.md) | `text` |
| [quantity.md](quantity.md) | `quantity` |
| [designation.md](designation.md) | `designation` |

**Count:** 15 type contracts (+ [00-START-HERE.md](00-START-HERE.md) index, [01-shared-node-contract.md](01-shared-node-contract.md) shared rules).

## Inline metadata (primary YAML only)

Each node uses its **primary YAML** as the canonical authoring surface. Do not author separate execution or nomenclature sidecar contract files.

| Metadata | Canonical location | Governing contract |
| --- | --- | --- |
| Paragraph / equation / validation_rule execution | Nested `execution:` block in the primary YAML | [paragraph.md](paragraph.md), [equation.md](equation.md), [validation-rule.md](validation-rule.md) |
| Workflow runtime (navigation, interactions, texts, …) | Nested `runtime:` block in `workflows/{machine-key}.yaml` | [workflow.md](workflow.md) |
| Paragraph-introduced parameters | `introduces_parameter` edges in the primary paragraph YAML | [paragraph.md](paragraph.md) §8–§9 |

**Nomenclature:** no `{id}.nomenclature.yaml` sidecar. Optional inline `nomenclature` on the primary paragraph file when used; otherwise use `introduces_parameter` edges.

**Legacy compatibility (read-only at load):** `engine/reference/paragraph_sidecar.py` and `equation_sidecar.py` may merge old `*.execution.yaml` files when present during pack load. That loader path is migration compatibility only — not an authoring surface or registry contract.

## Pack configuration

| File | Contract |
| --- | --- |
| `knowledge/standards/<publisher>/<pack>/pack.yaml` | [sidecars/pack-metadata.md](sidecars/pack-metadata.md) |

**Sidecar contracts on disk:** 1 (`pack-metadata.md` only). Pack defaults are the only supported sidecar authoring contract in this folder.

## Audit

```bash
python scripts/audit_current_node_yaml.py
```

Reports: `audits/reports/nodes/current-node-yaml-audit.md` and per-type projections listed in [00-START-HERE.md](00-START-HERE.md).
