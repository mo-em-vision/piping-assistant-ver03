# Global parameter ontology

Canonical engineering concepts (`PARAM-*`) shared across all standards packs.

## Purpose

Parameter nodes define **reusable engineering concepts** — not values, units, resolution strategy, or runtime state. Values belong to Facts in the Execution Context.

## Layout

| Path | Role |
|------|------|
| [nodes/](nodes/) | Canonical parameter ontology (`PARAM-*.yaml`) |

## Three-layer model

```
PARAM-*  ──has_dimension──►  DIM-*  ──references──►  UNIT-*
```

| Layer | Pack | Defines |
|-------|------|---------|
| Parameter | `parameters/` | Engineering concept (pressure, corrosion allowance, material) |
| Dimension | [`../dimensions/`](../dimensions/) | Compatible units for a quantity kind |
| Unit | [`../units/`](../units/) | Conversion between unit symbols |

Authoring template: [`docs/node-templates/Parameter Node.md`](../../../docs/node-templates/Parameter%20Node.md).

## Compile

```bash
python scripts/build_graph_db.py --pack knowledge/global/parameters
```

Cross-pack edges (`introduced_by`, `used_by` → standards nodes) compile when the full graph is built; the parameters pack alone resolves `has_dimension` edges to `DIM-*` nodes in the dimensions pack.
