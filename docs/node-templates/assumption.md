# Assumption Node Template

Expansion prerequisites evaluated before graph branches open.

**Preferred:** embed in a parent `definition` node under `assumptions:` (see [`embedded_source.md`](embedded_source.md)).

Standalone folder (legacy):

```yaml
---
id: B313-assumption-straight-pipe
type: parameter
kind: assumption
input_id: straight_pipe_section
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

Embedded in parent `node.yaml`:

```yaml
assumptions:
  - id: B313-assumption-straight-pipe
    type: parameter
    kind: assumption
    input_id: straight_pipe_section
    required_for_expansion: true
    requires_confirmation: true
    allowed_values: [true, false]
    blocks_expansion_on: [false]
    question: >
      Is the pipe wall thickness you would like to calculate for a straight section of pipe?
    expansion_block_message: Non-straight pipe sections are not yet supported.
    located_in: B313-304.1.1
```

## Required fields

| Field | Description |
|-------|-------------|
| `id` | Unique node id |
| `type` | `parameter` (canonical); legacy `assumption` normalizes to this |
| `kind` | Must be `assumption` |
| `input_id` | Task state field name (legacy `field` also accepted) |
| `required_for_expansion` | Must be true before dependent nodes expand |

## Optional fields

| Field | Description |
|-------|-------------|
| `allowed_values` | Valid answers |
| `blocks_expansion_on` | Values that halt expansion |
| `question` | User prompt |
| `expansion_block_message` | Message when expansion blocked |
