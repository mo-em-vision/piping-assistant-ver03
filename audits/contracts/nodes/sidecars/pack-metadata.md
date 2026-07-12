# Pack Metadata Sidecar Contract

## 1. Purpose

Pack metadata (`pack.yaml`) declares standards-pack defaults inherited by all child nodes in the pack — source language, authority binding, and edition — without repeating fields on every paragraph.

## 2. Use this sidecar when

- You are creating or maintaining a standards knowledge pack under `knowledge/standards/<publisher>/<pack>/`.
- All paragraphs in the pack share `source_language` for `text.original`.
- You need a single pack root identity (`id`, `authority`, `edition`).

## 3. Do not use this sidecar when

- You need node-specific execution or navigation (use paragraph or workflow sidecars).
- You are defining global ontology nodes (`knowledge/global/`).
- A field must differ per node (set on the node; node wins over pack defaults).

## 4. File location

`knowledge/standards/<publisher>/<pack>/pack.yaml`

Alternate filename: `pack.yml` (lower precedence if both exist).

## 5. ID convention

| Field | Rule |
| --- | --- |
| `id` | Pack machine id (`asme_b31.3`) — not a graph node id |
| `authority` | `AUTH-*` governing authority for the pack |
| `edition` | Active edition year or label |
| `source_language` | ISO language code (e.g. `en`) |

## 6. Copyable minimal YAML skeleton

```yaml
id: asme_b31.3
title: ASME B31.3 Process Piping
authority: AUTH-ASME-B31.3
edition: 2024
source_language: en
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `source_language` | Required for inheritance into paragraph `text` metadata |

Recommended: `id`, `title`, `authority`, `edition`.

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `title` | Human-readable pack name |
| `description` | Pack scope narrative |
| `publisher` | Issuing organization |
| `revision_year` | Pack content revision |
| Additional keys | Ignored unless future loaders define inheritance |

Only `source_language` is actively merged into child node metadata today.

## 9. Forbidden fields

```text
edges, links, navigation, interactions, requires, calculates,
paragraph_number, type (node type)
```

Pack metadata is not a graph node — do not author node-level execution or relationship fields.

## 10. Permitted outgoing relationships

Pack metadata does not use `edges`. Reference `AUTH-*` by id in the `authority` field. Child paragraphs link via their own `belongs_to_authority` edges.

## 11. Fields consumed by runtime components

Graph compile loads pack metadata at pack root and applies inheritable fields to each child node. `apply_pack_metadata` injects `text.source_language` when absent on paragraph nodes. Edition and authority on pack inform pack-level indexing; paragraph nodes carry their own `authority` and `edition` for validation.

## 12. Validation procedure

1. Confirm `pack.yaml` exists at pack root.
2. Confirm `source_language` is non-empty.
3. Confirm `authority` references an existing `AUTH-*` node.
4. Rebuild: `python scripts/build_graph_db.py` and `python scripts/build_standards_nodes_db.py`.
5. Confirm paragraph validator rejects `text.source_language` on individual nodes when pack supplies it.

## 13. Common authoring mistakes

- Setting `text.source_language` on every paragraph instead of `pack.yaml`.
- Omitting `pack.yaml` and losing language inheritance.
- Treating pack `id` as a paragraph or workflow graph id.
- Putting execution sidecar keys in `pack.yaml`.
- Mismatched `authority` between pack and paragraph nodes.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/pack.yaml`

## 15. Implementation evidence appendix

- Loader: `engine/reference/pack_metadata.py` — `load_pack_metadata`, `apply_pack_metadata`, `_PACK_FILENAMES`
- Inheritance rule: `apply_pack_metadata` merges `source_language` into `metadata.text` when node lacks it
- Paragraph validation: `engine/validation/paragraph_node_validator.py` — rejects `text.source_language` on nodes
- Graph build: pack root discovery during `engine/graph/graph_builder.py` compile
