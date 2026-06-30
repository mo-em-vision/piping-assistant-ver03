# B31.3 micro-graph node move map

Historical relocations from `graph/nodes/*` into the `nodes/` tree. **Current layout (2026):** flat `nodes/{node_id}/` folders — see [`b313_folder_flatten_summary.md`](b313_folder_flatten_summary.md).

## Flat target paths (current)

| Canonical id | Target (`nodes/`) | Notes |
| --- | --- | --- |
| `B313-WF-PIPE-WALL-THICKNESS` | `B313-WF-PIPE-WALL-THICKNESS/` | workflow root |
| `B313-WF-MAWP` | `B313-WF-MAWP/` | workflow root |
| `B313-304.1.1` | `B313-304.1.1/` | definition; was `304/304.1/304.1.1/` |
| `B313-304.1.2` | `B313-304.1.2/` | calculation |
| `B313-304.1.3` | `B313-304.1.3/` | calculation stub |
| `B313-MAWP-SECTION` | `B313-MAWP-SECTION/` | MAWP definition (yaml id); was `304/304.1/mawp_definition/` |
| `B313-MAWP-CALCULATION` | `B313-MAWP-CALCULATION/` | MAWP calculation |
| `B313-302.3.3` | `B313-302.3.3/` | was `302/302.3.3/B313-302.3.3/` |
| `B313-302.3.5` | `B313-302.3.5/` | was `302/302.3.5/B313-302.3.5/` |
| `B313-table-*` | `B313-table-*/` | was under `appendix_A/tables/` or section `tables/` |
| `B313-note-*` | `B313-note-*/` | table footnotes |
| `B313-param-*` | `B313-param-*/` | was `parameters/B313-param-*/` |
| `B313-quantity-*` | `B313-quantity-*/` | was `quantities/` |
| `B313-designation-*` | `B313-designation-*/` | was `designations/` |
| `B313-lookup-allowable-stress` | `B313-lookup-allowable-stress/` | was `appendix_A/lookups/allowable-stress/` |
| `B313-table-A-1-REF` | `B313-table-A-1-REF/` | was `appendix_A/tables/B313-table-A-1-ref/` |

Embedded children (compiled from parent metadata, no standalone folder):

| Id | Parent folder | Container |
| --- | --- | --- |
| `B313-304.1.1-init-text` | `B313-304.1.1/` | `texts` |
| `B313-assumption-straight-pipe` | `B313-304.1.1/` | `assumptions` |
| `B313-interaction-pressure-loading` | `B313-304.1.1/` | `interactions` |
| `B313-eq-2` | `B313-304.1.1/` | `equations` |
| `B313-eq-wall-thickness` | `B313-304.1.2/` | `equations` |
| `B313-eq-mawp` | `B313-MAWP-SECTION/` | `equations` |

## Authoring layout (current)

Section nodes use a **single `node.yaml`** (frontmatter + optional markdown body):

- Frontmatter — `type`, `contains`, `requires`, `assumptions`, `interactions`, `equations`, `nomenclature`, embedded `source:` blocks
- Body — standard paragraph text and LaTeX after the closing `---`

Dual `node.yaml` + `node.md` pairs were merged in 2026-06-30 (`scripts/merge_b313_node_sources.py`). Table and note nodes may still use `node.md` only.

Child nodes listed above are compiled from parent metadata containers via `engine/reference/embedded_nodes.py`. Redundant per-child folders were removed during flatten migration; `file:` paths remain as graph aliases.

Graph DB aliases: `B313-304.1.{1,2,3}-SECTION` → canonical section ids; `nodes/B313-304.1.1` → `B313-304.1.1`.

See also: [`embedded_source.md`](../node-templates/embedded_source.md).
