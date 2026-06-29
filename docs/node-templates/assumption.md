# Assumption Node Template

Expansion prerequisites evaluated before graph branches open.

```yaml
---
id: B313-assumption-straight-pipe
type: assumption
field: straight_pipe_section
title: Straight pipe section

description: >
  Applied to a straight section of a pipe.

required_for_expansion: true
requires_confirmation: true
allowed_values: [true, false]
blocks_expansion_on: [false]

question: >
  Is the pipe wall thickness you would like to calculate for a straight section of pipe?

expansion_block_message: >
  Non-straight pipe sections are not yet supported.

edges:
  - to: B313-304.1.1
    type: located_in
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | Must be `assumption` |
| `field` | Task state field name |
| `required_for_expansion` | Must be true before dependent nodes expand |

## Optional fields

| Field | Description |
|-------|-------------|
| `allowed_values` | Valid answers |
| `blocks_expansion_on` | Values that halt expansion |
| `question` | User prompt |
| `expansion_block_message` | Message when expansion blocked |
