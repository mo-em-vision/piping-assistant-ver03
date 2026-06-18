# Intent Detection (Planner)

Extract structured engineering intent from user language.

## Output JSON

```json
{
  "action": "verify",
  "object": "pipe integrity",
  "domain": "piping",
  "workflow": "pipe_wall_thickness_design",
  "confidence": 0.0
}
```

## Rules

- Do not calculate or execute engineering logic.
- Use `null` workflow when intent is ambiguous.
