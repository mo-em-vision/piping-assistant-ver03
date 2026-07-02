# Global parameter ontology

Canonical parameter roles (`PARAM-*`) shared across all standards packs.

## Purpose

Parameter nodes define **contextual engineering roles** — not values, units, resolution strategy, or runtime state. Semantic meaning lives in [`../concepts/`](../concepts/) (`CONCEPT-*`); values belong to Facts in the Execution Context.

## Layout

| Path | Role |
|------|------|
| [nodes/](nodes/) | Canonical parameter ontology (`PARAM-*.yaml`) |

## Four-layer model

```
CONCEPT-*  ──has_parameter──►  PARAM-*  ──has_dimension──►  DIM-*  ──allows_unit──►  UNIT-*
```

| Layer | Pack | Defines |
|-------|------|---------|
| Concept | [`../concepts/`](../concepts/) | Semantic engineering meaning |
| Parameter | `parameters/` | Contextual role (design pressure, corrosion allowance, …) |
| Dimension | [`../dimensions/`](../dimensions/) | Compatible units for a quantity kind |
| Unit | [`../units/`](../units/) | Conversion between unit symbols |

Authoring template: [`docs/node-templates/Parameter Node.md`](../../../docs/node-templates/Parameter%20Node.md).

## Compile

```bash
python scripts/build_graph_db.py --pack knowledge/global/parameters
```

Cross-pack edges (`introduced_by`, `used_by` → standards nodes) compile when the full graph is built; the parameters pack alone resolves `has_dimension` edges to `DIM-*` nodes in the dimensions pack.
