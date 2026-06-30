# Embedded Child Nodes (`source:`)

Parent section nodes (`type: definition` or `type: calculation`) can declare child objects inline in metadata containers instead of authoring a separate folder per child.

`GraphBuilder`, `StandardsNodesDatabase`, and `StandardsReader` extract these via `engine/reference/embedded_nodes.py`. Each embedded child becomes a first-class graph node with its own id, type, and aliases.

## Supported containers

On the parent node (or within `subsections[]`):

| Container | Default child type | Default `kind` |
|-----------|-------------------|----------------|
| `assumptions` | `parameter` | `assumption` |
| `interactions` | `parameter` | `interaction` |
| `equations` | `equation` | — |
| `texts` | `text` | `section` |
| `notes` | `text` | `note` |
| `criteria` | `text` | — |
| `conditions` | `text` | `condition` (when not overridden) |

## Entry shape

Each list item needs an `id` (or `node_id`). Optional fields:

| Field | Purpose |
|-------|---------|
| `file` | Legacy relative path; registered as a graph alias |
| `source` | Inline YAML frontmatter + markdown body (preferred for migrated nodes) |
| `text` / `body` | Short inline prose when no `source` block is needed |
| `type` / `kind` | Override defaults (e.g. `type: equation`) |

### `source:` block format

The `source` value is a literal block containing a full mini-node:

```yaml
equations:
  - id: B313-eq-2
    type: equation
    file: equations/eq_2_minimum_required_thickness.md
    source: |
      ---
      equation_id: eq-2
      sympy: "t_m = t + c"
      display_latex: "t_m = t + c"
      requires:
        - node_id: B313-quantity-thickness
          alias: t
          priority: 85
      calculates:
        - B313-param-t_m
      ---
      # Minimum Required Thickness (eq. 2)
```

Frontmatter delimiters use **line-based** `---` parsing (safe when markdown tables or prose contain triple dashes).

### Resolution order

When reading equation or note content at runtime:

1. External file at `record.path.parent / file` if it exists on disk
2. Embedded `source` frontmatter merged with the list entry metadata
3. `find_embedded_body()` walk of parent metadata by `file` or `id`

## Dual-file parents

Section nodes commonly pair:

- `node.yaml` — canonical structure (`contains`, `assumptions`, `equations`, `texts`, …)
- `node.md` — paragraph trace and fuller embedded `source:` blocks

When both exist, **YAML wins** for graph discovery; markdown supplies paragraph body and may duplicate or extend embedded children.

## Example: assumption embedded in definition node

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
```

## Example: note embedded in table node

```yaml
notes:
  - id: note_1
    node_id: B313-note-302-3-3C-1
    type: text
    kind: note
    file: B313-note-302-3-3C-1/node.md
    source: |
      ---
      id: B313-note-302-3-3C-1
      type: requirement
      title: "Table 302.3.3C — Note (1)"
      depends_on:
        - node_id: B313-table-302-3-3C
      ---
      # Note (1) to Table 302.3.3C
      Machine all surfaces to a finish of 6.3 µm Ra ...
```
