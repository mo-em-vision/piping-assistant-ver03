# Workflows

Engineering workflow entry points (not part of `knowledge/`). Workflows are standard-agnostic; linkage to standards packs is via `expected_authorities` in each workflow YAML.

## Layout

```
workflows/
├── pipe-wall-thickness.yaml
├── mawp.yaml
├── WF-PIPE-WALL-THICKNESS/runtime.yaml
└── WF-MAWP/runtime.yaml
```

## Compile

```bash
python scripts/build_standards_tasks_db.py
```

Produces `knowledge/standards/workflows.db`. Pack graph compile loads matching workflows via `engine/graph/graph_builder.py` (matched by pack `authority`).
