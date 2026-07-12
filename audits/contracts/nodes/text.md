# Text Node Contract

## 1. Purpose

A text node stores human-readable explanatory prose — workflow initiation copy, equation introductions, result explanations, and table captions — for presentation without engineering calculation semantics.

## 2. Use this node when

- You need initiation or explanatory prose in the center panel.
- An equation or section needs an introductory paragraph separate from the authoritative standard text.
- You are authoring table notes or captions (`kind: note`) — prefer `table_note` for standards table footnotes; see [table-note.md](table-note.md).

## 3. Do not use this node when

- You need official standard paragraph text (use `paragraph` with `text.original`).
- You need a formula (use `equation`).
- You need gatherable user input (use `parameter`).

## 4. File location

| Form | Path |
| --- | --- |
| Standalone | `knowledge/**/nodes/**/{id}.yaml` with `type: text` |
| Embedded | Parent `node.yaml` under `texts:` container (preferred for section nodes) |
| Workflow sidecar | `workflows/{WF-ID}/runtime.yaml` under `texts:` |

## 5. ID convention

| Field | Rule |
| --- | --- |
| `id` | Descriptive slug (`pipe-wall-init-text`, `asme-b313-table-302-3-3-1-note-1`) |
| `role` | `initiation`, `equation_intro`, `result_explanation`, or `caption` |
| `kind` | Optional variant (`section`, `note`) |

## 6. Copyable minimal YAML skeleton

Standalone:

```yaml
---
id: TEXT-example-intro
type: text
title: Example Introduction
role: initiation
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---

Example explanatory prose for the center panel.
```

Embedded in parent (no full frontmatter file):

```yaml
texts:
  - id: TEXT-example-intro
    type: text
    kind: section
    role: equation_intro
    title: Equation introduction
    text: >
      Example introduction to the governing equation.
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Unique within scope |
| `type` | `text` |
| `role` | One of: `initiation`, `equation_intro`, `result_explanation`, `caption` |
| `metadata.last_revision`, `metadata.edited_by` | When standalone YAML file |

Body content via markdown below frontmatter, or `text:` / `title:` fields when embedded.

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `title` | Display heading |
| `display_order` | Sort order among sibling texts |
| `kind` | `section`, `note`, etc. |
| `documentation.description` | Longer narrative for embedded texts |
| `edges` | `explains`, `depends_on` targets |
| `paragraph` | Citation string for table notes |
| `topic`, `section` | Topical indexing |

## 9. Forbidden fields

```text
value, user_input, runtime_value, fact_value, formula, requires,
calculates, lookup, equation_class, parameter_class
```

Also forbidden:

- Engineering execution fields on text nodes
- Top-level `links` block (use `edges`)

## 10. Permitted outgoing relationships

| Edge type | Target | Notes |
| --- | --- | --- |
| `explains` | equation / paragraph id | What this text introduces |
| `depends_on` | table / paragraph id | Context dependency |
| `related_to` | any node | Loose association |

## 11. Fields consumed by runtime components

Flow guidance and presentation layers read `texts` blocks for initiation and result narration. Response composer may emit text blocks with `role` for center-panel display. Embedded texts compile as first-class nodes via `embedded_nodes`. Workflow runtime sidecar `texts` merge into workflow metadata at load.

## 12. Validation procedure

No dedicated validator. Validate manually:

1. Confirm `type: text` and valid `role`.
2. Confirm revision metadata on standalone files.
3. Confirm body content is non-empty for user-visible texts.
4. When embedded, confirm parent compiles via `python scripts/build_graph_db.py`.
5. Run presentation/guidance tests when changing workflow texts.

## 13. Common authoring mistakes

- Using `paragraph` nodes for non-authoritative UI copy.
- Invalid `role` strings outside the four allowed values.
- Omitting `display_order` when multiple texts compete for sort position.
- Putting prompt questions on text nodes (belong on `PARAM-*`).
- Using legacy `to:` instead of `target:` on edges in new authoring.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-1-note-1.yaml` (see [table-note.md](table-note.md) for table footnotes)
- `workflows/WF-PIPE-WALL-THICKNESS/runtime.yaml` (embedded `texts:` entries)
- Standalone example id pattern: `B313-eq-2-intro`

## 15. Implementation evidence appendix

- Embedded compile: `engine/reference/embedded_nodes.py` — `_EMBEDDED_NODE_CONTAINER_KEYS`, `texts` default type
- Workflow merge: `engine/reference/workflow_sidecar.py` — `_RUNTIME_KEYS` includes `texts`
- Embedded defaults: `engine/reference/embedded_nodes.py`
- Guidance: `presentation/guidance/workflows/`
