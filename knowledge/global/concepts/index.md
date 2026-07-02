# Global engineering concept ontology

Canonical semantic engineering concepts (`CONCEPT-*`) shared across all standards packs.

## Purpose

Concept nodes define **reusable semantic engineering meaning** — not values, units, or runtime state. Parameters (`PARAM-*`) are contextual roles of concepts; Facts store runtime values.

## Layout

| Path | Role |
|------|------|
| [nodes/](nodes/) | Engineering concept ontology (`CONCEPT-*.yaml`) |

## Four-layer model

```
CONCEPT-*  ──has_parameter──►  PARAM-*  ──has_dimension──►  DIM-*  ──allows_unit──►  UNIT-*
```

| Layer | Pack | Defines |
|-------|------|---------|
| Concept | `concepts/` | Semantic engineering meaning |
| Parameter | [`../parameters/`](../parameters/) | Contextual role (design pressure, corrosion allowance, …) |
| Dimension | [`../dimensions/`](../dimensions/) | Compatible units for a quantity kind |
| Unit | [`../units/`](../units/) | Conversion between unit symbols |

Authoring template: [`docs/node-templates/Engineering Concept Node Template.md`](../../../docs/node-templates/Engineering%20Concept%20Node%20Template.md).

## Compile

```bash
python scripts/build_graph_db.py --pack knowledge/global/concepts
```

Cross-pack edges (`has_parameter` → `PARAM-*`, `has_dimension` → `DIM-*`) compile when sibling ontology packs are merged; the concepts pack alone loads concept node metadata.
