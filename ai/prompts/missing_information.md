# Missing Information

Explain why a specific engineering input is required.

Return JSON:

```json
{
  "input_id": "design_pressure",
  "symbol": "P",
  "reason": "Required by ASME B31.3 §304.1.1 for thickness calculation.",
  "node_id": "304.1.2-a"
}
```

Use the node reference when provided. Do not fabricate paragraph requirements.
