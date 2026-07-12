# Knowledge Nodes — Start Here

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
| Global units / dimensions / concepts / authorities | `knowledge/global/{units,dimensions,concepts,authorities}/nodes/` |
| Workflows | `workflows/{slug}.yaml` with runtime sidecar `workflows/{WF-ID}/runtime.yaml` |
| Pack defaults | `knowledge/standards/<publisher>/<pack>/pack.yaml` |

Sidecars (execution, nomenclature, runtime) live beside or under the parent node — see [sidecars/](sidecars/).

## How to create a node

1. Choose the node type from the table above and open its contract.
2. Copy the **minimal YAML skeleton** from section 6 of that contract.
3. Set `id` equal to the filename stem (`304.1.2-a.yaml` → `id: 304.1.2-a`).
4. Fill required fields; add typed `edges` only (never a top-level `links` block).
5. Set `metadata.last_revision` (ISO date) and `metadata.edited_by` on every edit.
6. If the node needs execution or navigation metadata, use a **sidecar** instead of bloating frontmatter.
7. Rebuild graph caches when working with standards packs: `python scripts/build_graph_db.py`.

## How to validate a node

| Node types with dedicated validators | Command / module |
| --- | --- |
| `paragraph`, `parameter`, `equation`, `lookup`, `validation_rule`, `workflow`, `unit`, `authority` | `engine/validation/*_node_validator.py` (also exercised in pytest) |
| `concept` | `tests/reference/test_concept_ontology.py` |
| `dimension` | `tests/units/test_physical_dimensions.py` |
| `text`, `quantity`, `designation`, `table` | Contract + `validate_revision_metadata`; run `python scripts/audit_current_node_yaml.py` |

Run targeted tests after edits:

```bash
python -m pytest tests/reference/test_concept_ontology.py tests/units/test_physical_dimensions.py -q
python -m pytest tests/graph -q
```

## Sidecar contracts

When frontmatter would hold runtime-adjacent fields, split them into sidecars:

| Sidecar | Contract |
| --- | --- |
| Paragraph execution (`*.execution.yaml`) | [sidecars/paragraph-execution.md](sidecars/paragraph-execution.md) |
| Paragraph nomenclature (`nomenclature.yaml`) | [sidecars/paragraph-nomenclature.md](sidecars/paragraph-nomenclature.md) |
| Equation execution (`*.execution.yaml`) | [sidecars/equation-execution.md](sidecars/equation-execution.md) |
| Workflow runtime (`runtime.yaml`) | [sidecars/workflow-runtime.md](sidecars/workflow-runtime.md) |
| Pack metadata (`pack.yaml`) | [sidecars/pack-metadata.md](sidecars/pack-metadata.md) |

## Related contracts

- Shared rules: [01-shared-node-contract.md](01-shared-node-contract.md)
- Runtime Facts / Goals: [../runtime/](../runtime/) (when published)
- Rendering output: [../Global Rendering Contract.md](../Global%20Rendering%20Contract.md)
- Authoring contracts (protected): `audits/contracts/nodes/`
