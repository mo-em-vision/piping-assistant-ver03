# Node Selection (Planner)

Rank candidate workflow roots when multiple graph entry points apply.

## Output JSON

```json
{
  "selected_root": "pipe_wall_thickness_design",
  "candidate_roots": ["pipe_wall_thickness_design"],
  "confidence": 0.0,
  "reason": "Best match for stated intent"
}
```

## Rules

- Prefer implemented roots under `standards/asme_b31.3/roots/`.
- Do not invent nodes that are not in the standards pack.
