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

Authoring template: [`docs/node-templates/Engineering Concept.md`](../../../docs/node-templates/Engineering%20Concept.md).

## Canonical concepts

| Node | Class | Dimension |
|------|-------|-----------|
| `CONCEPT-pressure` | physical_quantity | `DIM-pressure` |
| `CONCEPT-wall-thickness` | geometric_quantity | `DIM-length` |
| `CONCEPT-corrosion` | geometric_quantity | `DIM-length` |
| `CONCEPT-pipe-diameter` | geometric_quantity | `DIM-length` |
| `CONCEPT-stress` | physical_quantity | `DIM-pressure` |
| `CONCEPT-temperature` | physical_quantity | `DIM-temperature` |
| `CONCEPT-allowable-stress` | physical_quantity | `DIM-pressure` |
| `CONCEPT-material` | material | — |
| `CONCEPT-pipe-construction` | selection | — |
| `CONCEPT-weld-joint-efficiency` | factor | — |
| `CONCEPT-temperature-coefficient` | coefficient | — |

## Compile

```bash
python scripts/build_graph_db.py --pack knowledge/global/concepts
```

Cross-pack edges (`has_parameter` → `PARAM-*`, `has_dimension` → `DIM-*`) compile when sibling ontology packs are merged; the concepts pack alone loads concept node metadata.
