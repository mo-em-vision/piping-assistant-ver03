# Global physical dimensions

Quantity kinds (pressure, length, temperature, velocity, …) and their allowed unit nodes.

## Layout

| Path | Role |
|------|------|
| [nodes/](nodes/) | Physical dimension ontology (`DIM-*.yaml`) |
| [registry.yaml](registry.yaml) | Pipe NPS/schedule dimension source registry (ASME B36.10) |

Dimension nodes reference unit node ids under [`../units/nodes/`](../units/nodes/).

## Compile

Physical dimension nodes compile with the same graph builder as the unit pack:

```bash
python scripts/build_graph_db.py --pack knowledge/global/dimensions
```

(Or invoke `GraphBuilder` on `knowledge/global/dimensions` in tests.)
