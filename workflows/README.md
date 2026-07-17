# Workflows

Engineering workflow entry points (not part of `knowledge/`). Workflows are standard-agnostic; linkage to standards packs is via `expected_authorities` in each workflow YAML.

## Layout

```
workflows/
├── pipe-wall-thickness.yaml
└── mawp.yaml
```

Deterministic runtime metadata (`navigation`, `interactions`, `texts`, `documentation`, etc.) lives in the nested `runtime:` block inside each primary workflow YAML — not in separate sidecar files.

## Compile

```bash
python scripts/build_standards_tasks_db.py
```

Produces `knowledge/standards/workflows.db`. Pack graph compile loads matching workflows via `engine/graph/graph_builder.py` (matched by pack `authority`).
