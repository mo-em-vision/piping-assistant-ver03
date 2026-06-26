# ASME B31.3 Standard Pack

Self-contained engineering knowledge for ASME B31.3 Process Piping.

## Layout

```
asme_b31.3/
├── index.md          # navigation links only
├── readme.md
├── asme_b313_tables.db   # compiled lookup tables (from nodes/**/tables/)
├── nodes/            # paragraph / calculation knowledge units (grouped by section)
│   ├── 302/
│   │   ├── 302.3.3/          # casting quality factor E_c
│   │   │   ├── B313-302.3.3/
│   │   │   └── tables/       # Table 302.3.3C + notes
│   │   └── 302.3.5/          # weld joint strength reduction W
│   │       ├── B313-302.3.5/
│   │       └── tables/
│   ├── 304/                  # pressure design thickness
│   │   ├── 304.1.1/
│   │   │   └── tables/       # Table 304.1.1 coefficient Y
│   │   ├── 304.1.2/
│   │   └── 304.1.3/
│   └── appendix_A/tables/    # Tables A-1, A-1A, A-1B (allowable stress + quality factors)
├── templates/
└── reports/
```

Workflow entry points live under `standards/tasks/<standard_slug>/` (e.g. `standards/tasks/asme_b31.3/pipe_wall_thickness_design/`).

Figure assets belong under the relevant node folder (e.g. `nodes/304/304.1.2/figures/`) when needed, not at pack root.

## Sample implementation

The first sample nodes follow `docs/core/7. node_structure_design.md` and `docs/core/8. Node Template.md`:

- `nodes/304/304.1.1/` — definition node: nomenclature, expansion interactions, eq. 2 (`t_m = t + c`)
- `nodes/304/304.1.2/` — internal pressure wall thickness (`t = PD / 2(SEW + PY)`, §304.1.2)
- `nodes/304/304.1.3/` — external pressure path
- `nodes/302/302.3.5/B313-302.3.5/` — W factor reference (Table 302.3.5)
- `nodes/appendix_A/tables/B313-table-A-1/` — allowable stress lookup (Table A-1)
- `standards/tasks/asme_b31.3/pipe_wall_thickness_design/` — pipe wall thickness workflow entry point

Node IDs (`B313-*`) are stable across the graph; folder paths mirror the standard's section hierarchy.

Nodes do not repeat the standard name in metadata; the parent folder defines the standard context.
