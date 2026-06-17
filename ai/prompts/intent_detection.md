# Intent Detection (shared)

Classify whether a user message is an engineering task request related to:

- pipe wall thickness design (`pipe_wall_thickness_design`)
- piping inspection / fitness-for-service
- unrelated / general conversation

Return JSON:

```json
{
  "is_engineering_request": true,
  "category": "pipe_wall_thickness_design | inspection | unrelated",
  "confidence": 0.0
}
```

Do not guess when confidence is below 0.6.
