# Paragraph Nomenclature Sidecar Contract

## 1. Purpose

The paragraph nomenclature sidecar stores structured symbol tables and nomenclature prose extensions for nomenclature paragraphs, merged into paragraph metadata at load time.

## 2. Use this sidecar when

- A paragraph introduces equation variables (`metadata.kind: nomenclature` or `introduces_parameter` edges only).
- Symbol definitions are too large for `text.original` alone.
- You need structured `nomenclature` entries consumed by the nomenclature resolver.

## 3. Do not use this sidecar when

- Symbols are already fully covered by `text.original` and `introduces_parameter` edges suffice.
- You need execution branching (use execution sidecar).
- You are defining global `PARAM-*` semantics (use parameter nodes).

## 4. File location

| Layout | Path |
| --- | --- |
| Flat file | `knowledge/standards/<pack>/nodes/paragraph/{id}.nomenclature.yaml` |
| Directory | `knowledge/standards/<pack>/nodes/paragraph/{id}/nomenclature.yaml` |

## 5. ID convention

No separate node `id`. Inherits parent paragraph id. The `nomenclature` key wraps the structured content.

## 6. Copyable minimal YAML skeleton

```yaml
nomenclature:
  symbols:
    - symbol: P
      parameter: PARAM-internal-design-gage-pressure
      description: Internal design gage pressure
    - symbol: D
      parameter: PARAM-outside-diameter
      description: Outside diameter of pipe
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `nomenclature` | Root key when file is non-empty |

Within `nomenclature`, symbol entries should map `symbol` to `PARAM-*` ids introduced by the parent paragraph.

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `nomenclature.symbols` | List of symbol definitions |
| `nomenclature.sections` | Grouped symbol tables |
| `nomenclature.notes` | Authoring notes |
| Per-symbol `unit` | Display unit hint |
| Per-symbol `description` | Definition beyond prose |

## 9. Forbidden fields

```text
id, type, edges, links, interactions, applicability, equations
```

Do not author `references_equation`, `references_table`, or `related_to` in the sidecar — those belong on paragraph `edges` (nomenclature paragraphs restrict edge types).

## 10. Permitted outgoing relationships

Nomenclature sidecars do not use `edges`. Link parameters via `parameter:` fields inside `nomenclature.symbols` and via parent paragraph `introduces_parameter` edges.

## 11. Fields consumed by runtime components

Nomenclature resolver merges sidecar `nomenclature` into paragraph metadata for symbol table display and equation binding. Equations reference nomenclature paragraphs via `nomenclature_ref`. Messaging may use symbol descriptions for equation variable prompts.

## 12. Validation procedure

1. Confirm parent paragraph is nomenclature-class (only `belongs_to_authority` and `introduces_parameter` edges).
2. Confirm each `parameter` in symbols matches an `introduces_parameter` edge target.
3. Confirm file naming matches paragraph id.
4. Rebuild graph and run nomenclature-related tests.

## 13. Common authoring mistakes

- Adding `references_*` edges on nomenclature paragraphs.
- Introducing parameters only in sidecar without `introduces_parameter` edges.
- Putting execution `interactions` in nomenclature sidecar.
- Using parenthetical paragraph ids in symbol cross-refs.
- Duplicating full `text.original` in sidecar verbatim without structure.

## 14. Current repository examples

Nomenclature content currently inline in paragraph frontmatter:

- `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-b.yaml`

Equation reference to nomenclature paragraph:

- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3a.yaml` (`nomenclature_ref: 304.1.1-b`)

## 15. Implementation evidence appendix

- Loader: `engine/reference/paragraph_sidecar.py` — `merge_paragraph_sidecar_metadata` (nomenclature path branch)
- Nomenclature edges: `engine/validation/paragraph_node_validator.py` — `_ALLOWED_NOMENCLATURE_EDGE_TYPES`, `_is_nomenclature_paragraph`
- Resolver: `engine/reference/nomenclature_resolver.py`
