# Knowledge

Engineering knowledge data root: per-standard **packs** under `standards/` and shared **global ontologies** under `global/`.

## Purpose

Source-of-truth for standards graph nodes, lookup tables, material catalogs, and global unit/dimension registries. Compiled at runtime or offline into SQLite caches (`*_graph.db`, `*_nodes.db`, etc.).

## Layout

```
knowledge/
├── standards/          # Per-standard packs (asme, api, astm) + cross-pack indexes
└── global/             # Shared ontologies (dimensions, units, datatypes)
```

## Entry Points

| Path | Role |
|------|------|
| `knowledge/standards/*/index.md` | Pack manifest |
| `scripts/build_all_standards_dbs.py` | Offline compile all DBs |
| `engine/reference/knowledge_paths.py` | Runtime path resolution |

## Dependencies

**Depends on:** nothing in application code (data only).

**Depended on by:** `engine/reference/standards_reader.py`, `engine/graph/graph_store.py`, `api/desktop_service.py`, build scripts under `scripts/`.

## Runtime Usage

**On execution path:** yes — every task loads packs via `CLIConfig.standards_root` → `knowledge/standards`.

## Compile path

```
knowledge/standards/*/nodes/*.yaml (+ *.md)
  → engine/graph/graph_builder.py
  → engine/reference/graph_compile.py
  → PackGraph / *_graph.db
```

## Notes

- Former repo path was `standards/` at repo root; global slices (`units/`, `pipe_dimensions/`) now live under `global/`.
- Per-node `nodes/B313-*/` folders are not documented individually — see pack `index.md` and node counts in group READMEs.

## Child documentation

- [standards/README.md](standards/README.md)
- [global/README.md](global/README.md)
