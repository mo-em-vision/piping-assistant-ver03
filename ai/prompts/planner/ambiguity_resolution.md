# Ambiguity Resolution (Planner)

Present workflow alternatives when the user request matches multiple engineering paths.

## Output JSON

```json
{
  "action": "clarify",
  "alternatives": [
    "Pipe wall thickness design",
    "Integrity verification",
    "Pressure test verification"
  ],
  "message": "Which engineering workflow should I continue with?"
}
```

## Rules

- List only plausible engineering workflows.
- Mark unimplemented workflows clearly when known.
