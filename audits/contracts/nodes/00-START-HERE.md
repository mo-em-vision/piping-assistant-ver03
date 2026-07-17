# Knowledge Nodes — Start Here

> **Authoring authority:** This index and the per-type contracts in this folder are the **sole source of truth** for new node YAML. They supersede narrative in [`docs/core/7. node_structure_design.md`](../../docs/core/7.%20node_structure_design.md). Enforcement: `engine/validation/*_node_validator.py` (do not edit validators during doc reconciliation).

## What are knowledge nodes?

Knowledge nodes are immutable YAML (and optional markdown body) files under `knowledge/` and `workflows/`. Each file declares one engineering object — a paragraph of standard text, a parameter definition, an equation, a lookup rule, a workflow objective, and so on. The graph compiler loads these files into a `PackGraph`; runtime execution reads the graph but never stores engineering truth back into node files.

Nodes are **not** task state. Values, user inputs, goal progress, and validation outcomes live in runtime models (Facts, Goals, Execution Context). See [Runtime contracts](../runtime/) for Facts and Goals.

## Which node type do I need?

| You are modeling… | Node type | Contract |
| --- | --- | --- |
| Official standard paragraph text | `paragraph` | [paragraph.md](paragraph.md) |
| Reusable engineering input/output field | `parameter` | [parameter.md](parameter.md) |
| Deterministic formula calculation | `equation` | [equation.md](equation.md) |
| Table-driven value resolution | `lookup` | [lookup.md](lookup.md) |
| Pass/fail or applicability check | `validation_rule` | [validation-rule.md](validation-rule.md) |
| End-to-end engineering task objective | `workflow` | [workflow.md](workflow.md) |
| Authoritative tabular data source | `table` | [table.md](table.md) |
| Measurement unit and conversion | `unit` | [unit.md](unit.md) |
| Physical or semantic dimension category | `dimension` | [dimension.md](dimension.md) |
| Broad engineering idea grouping parameters | `concept` | [concept.md](concept.md) |
| Governing standard, code, or specification | `authority` | [authority.md](authority.md) |
| Explanatory prose block | `text` | [text.md](text.md) |
| Standards table footnote | `table_note` | [table-note.md](table-note.md) |
| Physical quantity definition (legacy/embed) | `quantity` | [quantity.md](quantity.md) |
| Named classification (NPS, schedule, grade) | `designation` | [designation.md](designation.md) |

Read [01-shared-node-contract.md](01-shared-node-contract.md) before authoring any node type.

## Where do files live?

| Scope | Typical path pattern |
| --- | --- |
| Standards pack paragraphs | `knowledge/standards/<publisher>/<pack>/nodes/paragraph/{id}.yaml` |
| Standards pack equations | `knowledge/standards/<publisher>/<pack>/nodes/equation/{id}.yaml` |
| Standards pack lookups / tables | `knowledge/standards/<publisher>/<pack>/nodes/tables/{id}.yaml` |
| Standards pack validation rules | `knowledge/standards/<publisher>/<pack>/nodes/validation_rule/{id}.yaml` |
| Global parameters | `knowledge/global/parameters/nodes/PARAM-*.yaml` |
| Global units / dimensions / concepts / designations / authorities | `knowledge/global/{units,dimensions,concepts,designations,authorities}/nodes/` |
| Workflows | `workflows/{slug}.yaml` with nested `runtime` block in the same file |
| Pack defaults | `knowledge/standards/<publisher>/<pack>/pack.yaml` |

Shared datasets (large tables, SQLite caches, registries) remain separate files referenced by lookup nodes — not node sidecars.

## How to create a node

1. Choose the node type from the table above and open its contract.
2. Copy the **minimal YAML skeleton** from section 6 of that contract.
3. Set `id` equal to the filename stem (`304.1.2-a.yaml` → `id: 304.1.2-a`).
4. Fill required fields; add typed `edges` only (never a top-level `links` block).
5. Set `metadata.last_revision` (ISO date) and `metadata.edited_by` on every edit.
6. Place node-owned execution or workflow runtime metadata in nested `execution` / `runtime` blocks inside the primary YAML file.
7. Rebuild graph caches when working with standards packs: `python scripts/build_graph_db.py`.

## How to validate a node

| Node types with dedicated validators | Command / module |
| --- | --- |
| `paragraph`, `parameter`, `equation`, `lookup`, `validation_rule`, `workflow`, `unit`, `authority`, `table_note`, `dimension`, `concept`, `designation` | `engine/validation/*_node_validator.py` (also exercised in pytest) |
| `text`, `quantity`, `table` | Contract + `validate_revision_metadata`; run `python scripts/audit_current_node_yaml.py` |

Paragraph-specific audit (filtered projection of the same audit run):

```bash
python scripts/audit_current_node_yaml.py --filter paragraph
python scripts/audit_current_node_yaml.py --filter paragraph --pack asme_b31.3
```

Reports: `audits/reports/nodes/current-node-yaml-audit.md` (full), `audits/reports/nodes/paragraph-node-audit.md` (paragraph projection), `audits/reports/nodes/dimension-node-audit.md` (dimension projection), `audits/reports/nodes/concept-node-audit.md` (concept projection), `audits/reports/nodes/designation-node-audit.md` (designation projection), `audits/reports/nodes/authority-node-audit.md` (authority projection), `audits/reports/nodes/workflow-node-audit.md` (workflow projection), and `audits/reports/nodes/validation-rule-node-audit.md` (validation rule projection).

Concept audit:

```bash
python scripts/audit_current_node_yaml.py --filter concept
python scripts/audit_current_node_yaml.py --filter designation
python scripts/audit_current_node_yaml.py --filter authority
python scripts/audit_current_node_yaml.py --filter workflow
python scripts/audit_current_node_yaml.py --filter validation_rule
```

Paragraph field placement policy: `engine/reference/paragraph_authoring_policy.py`. Execution metadata must live under the nested `execution` block in the primary paragraph YAML.

Run targeted tests after edits:

```bash
python -m pytest tests/reference/test_paragraph_authoring_policy.py tests/reference/test_paragraph_audit_process.py tests/reference/test_paragraph_ontology.py -q
python -m pytest tests/reference/test_concept_ontology.py tests/units/test_physical_dimensions.py -q
python -m pytest tests/reference/test_authority_ontology.py tests/reference/test_authority_audit_process.py -q
python -m pytest tests/graph -q
```

## Pack and shared dataset configuration

| File | Contract |
| --- | --- |
| Pack metadata (`pack.yaml`) | [sidecars/pack-metadata.md](sidecars/pack-metadata.md) |

## Related contracts

- Shared rules: [01-shared-node-contract.md](01-shared-node-contract.md)
- Runtime Facts / Goals: [../runtime/](../runtime/) (when published)
- Rendering output: [../Global Rendering Contract.md](../Global%20Rendering%20Contract.md)
- Authoring contracts (protected): `audits/contracts/nodes/`
