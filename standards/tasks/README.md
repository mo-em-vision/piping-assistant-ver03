# Global workflow tasks

Cross-standard analysis entry points live here, grouped by standard slug:

```
tasks/
└── <standard_slug>/
    └── <task_slug>/
        └── root.md
```

Example: `tasks/asme_b31.3/pipe_wall_thickness_design/root.md`

Logical references use the path `tasks/<standard_slug>/<task_slug>/root.md` relative to `standards/`.

Compiled metadata is stored in `tasks/tasks.db` (built by `scripts/build_standards_tasks_db.py`).
