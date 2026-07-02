# Global unit ontology

Shared unit nodes with `belongs_to_dimension` and `converts_to` edges for all standards packs.

Each unit declares its dimension via `dimension: DIM-*` and links to the dimension node with a `belongs_to_dimension` edge.

Authoring template: [`docs/node-templates/Unit Node.md`](../../../docs/node-templates/Unit%20Node.md).

## Compile

```bash
python scripts/build_graph_db.py --pack knowledge/global/units
```

(Or invoke `GraphBuilder` on `knowledge/global/units` in tests.)
