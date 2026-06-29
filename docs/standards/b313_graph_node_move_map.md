# B31.3 micro-graph node move map

Relocates `graph/nodes/*` into the hierarchical `nodes/` tree. Section ids drop the `-SECTION` suffix.

| Source (`graph/nodes/`) | Target (`nodes/`) | Canonical id |
| --- | --- | --- |
| `B313-WF-PIPE-WALL-THICKNESS` | `workflows/B313-WF-PIPE-WALL-THICKNESS/` | unchanged |
| `B313-WF-MAWP` | `workflows/B313-WF-MAWP/` | unchanged |
| `B313-304.1.1-SECTION` | `304/304.1/304.1.1/` | `B313-304.1.1` |
| `B313-304.1.2-SECTION` | `304/304.1/304.1.2/` | `B313-304.1.2` |
| `B313-304.1.3-SECTION` | `304/304.1/304.1.3/` | `B313-304.1.3` |
| `B313-MAWP-SECTION` | `304/304.1/mawp_definition/` | unchanged |
| `B313-304.1.1-init-text` | `304/304.1/304.1.1/text/initiation/` | unchanged |
| `B313-assumption-straight-pipe` | `304/304.1/304.1.1/assumptions/straight-pipe/` | unchanged |
| `B313-interaction-pressure-loading` | `304/304.1/304.1.1/interactions/pressure-loading/` | unchanged |
| `B313-eq-2` | `304/304.1/304.1.1/equations/eq-2/` | unchanged |
| `B313-eq-2-intro` | `304/304.1/304.1.1/equations/eq-2-intro/` | unchanged |
| `B313-eq-2-result` | `304/304.1/304.1.1/equations/eq-2-result/` | unchanged |
| `B313-eq-wall-thickness` | `304/304.1/304.1.2/equations/wall-thickness/` | unchanged |
| `B313-eq-wall-thickness-intro` | `304/304.1/304.1.2/equations/wall-thickness-intro/` | unchanged |
| `B313-eq-wall-thickness-result` | `304/304.1/304.1.2/equations/wall-thickness-result/` | unchanged |
| `B313-eq-mawp` | `304/304.1/mawp_definition/equations/mawp/` | unchanged |
| `B313-lookup-allowable-stress` | `appendix_A/lookups/allowable-stress/` | unchanged |
| `B313-table-A-1-REF` | `appendix_A/tables/B313-table-A-1-ref/` | unchanged |
| `B313-param-*` | `parameters/B313-param-*/` | unchanged; `located_in: B313-304.1.1` |

Legacy browse `node.md` files at section paths are marked `status: superseded`. Legacy equation markdown under `equations/*.md` is superseded by sympy `node.yaml` children.

Graph DB aliases: `B313-304.1.{1,2,3}-SECTION` → canonical section ids.
