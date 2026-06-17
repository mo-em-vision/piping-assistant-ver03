# Node Selection

Given an engineering intent and available standards nodes, propose candidate root nodes.

Return JSON:

```json
{
  "root_nodes": ["roots/pipe_wall_thickness_design/root.md"],
  "confidence": 0.0,
  "alternatives": []
}
```

Prefer implemented roots under `standards/asme_b31.3/`. Record alternatives when the user may need a different path.
