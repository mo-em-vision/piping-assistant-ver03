# ASME B31.3 Standard Pack

Self-contained engineering knowledge for ASME B31.3 Process Piping.

## Layout

```
asme_b31.3/
├── index.md          # navigation links only
├── readme.md
├── asme_b313_tables.db   # compiled lookup tables (from nodes/**/tables/)
├── nodes/            # flat layout: one folder per node id (nodes/B313-*)
│   ├── B313-304.1.1/
│   ├── B313-304.1.2/
│   ├── B313-302.3.5/
│   ├── B313-table-A-1/
│   ├── B313-param-P/
│   └── B313-WF-PIPE-WALL-THICKNESS/
├── templates/
└── reports/
```

Workflow entry points live under `standards/tasks/<standard_slug>/` (e.g. `standards/tasks/asme_b31.3/pipe_wall_thickness_design/`).

Figure assets belong under the relevant node folder (e.g. `nodes/B313-304.1.2/figures/`) when needed, not at pack root.

## Sample implementation

The first sample nodes follow `docs/core/7. node_structure_design.md` and `docs/core/8. Node Template.md`:

- `nodes/B313-304.1.1/` — definition node: nomenclature, expansion interactions, eq. 2 (`t_m = t + c`)
- `nodes/B313-304.1.2/` — internal pressure wall thickness (`t = PD / 2(SEW + PY)`, §304.1.2)
- `nodes/B313-304.1.3/` — external pressure path
- `nodes/B313-302.3.5/` — W factor reference (Table 302.3.5)
- `nodes/B313-table-A-1/` — allowable stress lookup (Table A-1)
- `standards/tasks/asme_b31.3/pipe_wall_thickness_design/` — pipe wall thickness workflow entry point

Node IDs (`B313-*`) are stable across the graph; folder paths use `nodes/{node_id}/` for direct lookup (Ctrl+P by id).

Nodes do not repeat the standard name in metadata; the parent pack folder defines the standard context.
