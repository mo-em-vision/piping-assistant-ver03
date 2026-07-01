# Graph relationship schema

Every knowledge node uses a single relationship field:

```yaml
edges: []
```

Each edge has exactly:

```yaml
- type: <canonical relationship type>
  target: <node id>
```

## Stored edge types (outgoing only)

`parent`, `child`, `contains`, `contained_by`, `references`, `parameter`, `equation`, `material`, `table`, `figure`, `note`, `dataset`, `implements`, `depends_on`, `uses`, `requires`, `next`, `previous`, `related_to`, `derived_from`, `alias_of`

Reverse types (`referenced_by`, `dependency_of`, `required_by`, etc.) are computed by the graph index — never stored on nodes.

## Optional edge metadata

| Key | Purpose |
|-----|---------|
| `when` | Conditional routing |
| `alias`, `role` | Parameter binding |
| `subsection` | Paragraph/table subsection anchor |
| `factor`, `offset` | Unit conversion on `derived_from` |
| `reason` | Human-readable annotation |

## Non-graph citations

Prose trace links in nomenclature use `citations` (not `edges`):

```yaml
nomenclature:
  - symbol: t_m
    citations:
      - paragraph: 304.1.1(a)
      - equation: eq-2
        node_id: 304.1.1-eq-2
```
