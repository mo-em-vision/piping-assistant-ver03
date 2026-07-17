# Shared Node Contract

Rules that apply to **every** knowledge node unless a type-specific contract explicitly overrides them.

## 1. Purpose

Define the common on-disk shape, identity rules, and authoring boundaries for all immutable knowledge nodes in Ver03.

## 2. Use this node when

You are authoring or reviewing any file under `knowledge/**/nodes/` or workflow definition YAML under `workflows/`.

## 3. Do not use this node when

You need runtime task state (Facts, Goals, user values). Those belong in Execution Context models, not knowledge YAML.

## 4. File location

- One primary node per file: `{id}.yaml` (optional markdown body after frontmatter).
- Filename stem **must equal** `id`.
- Pack-scoped nodes live under `knowledge/standards/<pack>/nodes/<kind>/`.
- Global ontology nodes live under `knowledge/global/<kind>/nodes/`.
- Workflows live at `workflows/{machine-key}.yaml`.

## 5. ID convention

| Rule | Detail |
| --- | --- |
| Stability | `id` never changes after publication; rename by adding a new node and deprecating the old one. |
| Filename | `nodes/<kind>/{id}.yaml` — no extra prefixes in the path. |
| Canonical `type` | Must match one of the canonical kinds in `engine/reference/node_types.py`. |
| Pack prefixes | Standards equations use `asme-b313-*`; global params use `PARAM-*`; workflows use `WF-*`; etc. — see per-type contracts. |

### ID qualification (cross-type)

| Reference context | Id form | Example |
| --- | --- | --- |
| Paragraph `id` / `paragraph_number` within a pack | Bare hyphen subsection id | `304.1.2-a` |
| `authority.authorized_by` on equation, lookup, validation_rule (same pack) | Bare paragraph id in-pack | `304.1.2-a` |
| `introduced_by` on global `PARAM-*` | Pack-qualified paragraph id when citing standards prose | `asme-b313-304-1-1-b` |
| Global ontology nodes | Prefix per type contract | `PARAM-*`, `AUTH-*`, `WF-*` |
| Workflow entry | Repo `workflows/{machine-key}.yaml` slug | `pipe_wall_thickness_design` |

Do not pack-qualify `authority.authorized_by` paragraph ids when the governing paragraph is in the same standards pack as the node. Use pack-qualified ids for `introduced_by` when the parameter is global and the introducing paragraph is pack-scoped.

## 6. Copyable minimal YAML skeleton

Every node file opens with YAML frontmatter delimited by `---`:

```yaml
---
id: EXAMPLE-ID
type: <canonical_type>
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

Add type-specific required fields from the relevant type contract before committing.

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Stable identity; equals filename stem. |
| `type` | Canonical node type string. |
| `metadata.last_revision` | ISO date (`YYYY-MM-DD`) updated on every edit. |
| `metadata.edited_by` | Author or role string (e.g. `admin`). |

Type-specific contracts add further required fields (e.g. `paragraph_number`, `parameter_class`).

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `key` | Machine-safe slug for lookups and traces. |
| `name` / `title` | Human-readable label (type-dependent which is required). |
| `description` | Stable engineering definition. |
| `aliases` | Synonyms for search and display — not alternate ids. |
| `metadata.status` | Lifecycle (`active`, `draft`, `deprecated`) where applicable. |
| `metadata.version` | Integer or string version counter. |
| `edges` | Typed outgoing relationships — see section 10. |
| Markdown body | Long prose below frontmatter when needed. |

## 9. Forbidden fields

Never author runtime or execution-session fields on knowledge nodes:

```text
runtime_value, fact_value, user_input, execution_id, task_id,
calculation_result, selected_for_execution, active_in_context,
value, unit (on parameter), resolution, source, timestamp (on parameter),
workflow_id, project_id
```

Also forbidden on all nodes:

- Top-level `links` metadata block — use typed `edges` only.
- Duplicate relationship channels (e.g. `introduced_by` in `edges` when it belongs top-level on parameters).

Type-specific contracts list additional forbidden fields (e.g. `navigation` in workflow frontmatter).

## 10. Permitted outgoing relationships

All relationships use the edges array format:

```yaml
edges:
  - type: <taxonomy_edge_type>
    target: <target_node_id>
```

Rules:

- Outgoing edges only; inverses are compiled at query time.
- Use native taxonomy types documented in each type contract §10.
- Paragraph hierarchy (`parent`, ordered `children`) lives in `hierarchy` metadata — **not** in `edges`.
- `authorized_by` and `introduced_by` are compiled from dedicated top-level blocks on some types — do not duplicate in `edges`.

## 11. Fields consumed by runtime components

Graph compilation reads `id`, `type`, `edges`, and type-specific metadata to build `PackGraph`. Graph edges, node `applicability`, and equation `requires` / `calculates` dependencies determine which paths are active. Workflow `runtime.interactions` supplies workflow-level gate interaction metadata for pre-expansion decisions; it does not determine active paths or replace graph expansion. Execution kernel resolves parameter symbols from equation and lookup bindings. Messaging reads parameter prompt fields. Presentation layer reads `presentation`, `display`, and text bodies for rendered blocks.

## 12. Validation procedure

1. Confirm filename stem matches `id`.
2. Confirm `type` is canonical.
3. Confirm `metadata.last_revision` and `metadata.edited_by` are present.
4. Run the type-specific validator when one exists (see type contract section 12).
5. Confirm no forbidden fields and no `links` block.
6. Rebuild graph DB for standards packs and run pytest graph/reference tests.

## 13. Common authoring mistakes

- Setting `paragraph_number` to parenthetical form `304.1.2(a)` instead of hyphen id `304.1.2-a`.
- Putting `navigation`, `interactions`, or `assumptions` at workflow frontmatter top level instead of under nested `runtime:`.
- Authoring `hierarchy.previous` / `hierarchy.next` on paragraphs.
- Storing prompt copy only in the planner or frontend instead of on `PARAM-*` nodes.
- Using `calculates_parameter` on lookup nodes (use `returns_parameter`).
- Duplicating `authorized_by` in both `authority.authorized_by` and `edges`.

## 14. Current repository examples

- Shared revision pattern: any file under `knowledge/global/parameters/nodes/PARAM-allowable-stress.yaml`
- Edge taxonomy: `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.yaml`
- Pack defaults: `knowledge/standards/asme/asme_b31.3/pack.yaml`

## 15. Implementation evidence appendix

- Revision metadata: `engine/validation/node_revision_metadata.py` — `validate_revision_metadata`, `DEFAULT_LAST_REVISION`, `DEFAULT_EDITED_BY`
- Edge validation: `engine/reference/graph_compile.py` — `validate_edge_item`; `engine/reference/relationship_validator.py` — `RELATIONSHIP_RULES`
- No `links` block: `engine/reference/graph_compile.py` — `validate_no_links_metadata`
- Structural edge ban on paragraphs: `engine/validation/structural_edges.py` — `validate_no_structural_edges`
- Canonical types: `engine/reference/node_types.py`
- Embedded children: `engine/reference/embedded_nodes.py` — `_EMBEDDED_NODE_CONTAINER_KEYS`
- Sidecar merge: `engine/reference/paragraph_sidecar.py`, `equation_sidecar.py`, `workflow_sidecar.py`, `pack_metadata.py`
