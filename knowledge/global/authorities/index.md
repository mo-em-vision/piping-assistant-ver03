# Global authority ontology

Canonical authoritative engineering sources (`AUTH-*`) shared across all standards packs.

## Purpose

Authority nodes define **immutable authoritative sources** — standards, codes, regulations, and specifications. They do not store runtime values or execution state. [Authority Context](../../../docs/node-templates/Authority%20Context.md) selects which AUTH nodes are active for a task.

## Layout

| Path | Role |
|------|------|
| [nodes/](nodes/) | Authority ontology (`AUTH-*.yaml`) |

## Relationship to standards packs

```
AUTH-ASME-B31.3
  ├── contains → 304.1.1, 304.1.2 (paragraph nodes in asme_b31.3 pack)
  └── table → B313-table-A-1 (table nodes in asme_b31.3 pack)

Authority Context (runtime)
  └── active_authorities[].authority_id → AUTH-ASME-B31.3
```

Authoring template: [`docs/node-templates/Authority Node.md`](../../../docs/node-templates/Authority%20Node.md).

## Compile

```bash
python scripts/build_graph_db.py --pack knowledge/global/authorities
```

Cross-pack edges compile when sibling ontology and standards packs are merged; the authorities pack alone loads authority node metadata.
