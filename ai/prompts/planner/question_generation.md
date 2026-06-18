# Question Generation (Planner)

Turn missing graph inputs into user-friendly questions.

## Output JSON

```json
{
  "questions": [
    {
      "input_id": "design_temperature",
      "question": "To continue, I need the design temperature because allowable stress depends on metal temperature."
    }
  ]
}
```

## Rules

- Explain **why** each input is required.
- Reference the governing node or paragraph when known.
- Do not request inputs already satisfied by defaults or dependency outputs.
