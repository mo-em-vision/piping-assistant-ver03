# ASME B31.3 Standard Pack

Self-contained engineering knowledge for ASME B31.3 Process Piping.

## Layout

```
asme_b31.3/
├── pack.yaml         # pack defaults (source_language, authority, edition)
├── index.md          # navigation links only
├── readme.md
├── asme_b313_tables.db   # compiled lookup tables (from nodes/**/tables/)
├── nodes/            # flat layout: one folder per node id (nodes/B313-*)
│   ├── workflows/    # pipe-wall-thickness.yaml, mawp.yaml
│   ├── B313-304.1.1/
│   ├── 304.1.2-a/
│   ├── 302.3.5-e/
│   ├── B313-table-A-1/
│   ├── B313-param-P/
│   └── B313-WF-PIPE-WALL-THICKNESS/
```

Workflow entry points live at repo-root [`workflows/`](../../../../workflows/) (e.g. `pipe-wall-thickness.yaml`, `mawp.yaml`).

Figure assets belong under the relevant node folder (e.g. `nodes/304.1.2-a/figures/`) when needed, not at pack root.

## Sample implementation

The first sample nodes follow `docs/core/7. node_structure_design.md` and `docs/core/8. Node Template.md`:

- `nodes/B313-304.1.1/` — definition node: nomenclature, expansion interactions, eq. 2 (`t_m = t + c`)
- `nodes/304.1.2-a/` — internal pressure wall thickness (`t = PD / 2(SEW + PY)`, §304.1.2)
- `nodes/B313-304.1.3/` — external pressure path
- `nodes/302.3.5-e/` — W factor reference (Table 302.3.5)
- `nodes/B313-table-A-1/` — allowable stress lookup (Table A-1)
- [`workflows/pipe-wall-thickness.yaml`](../../../../workflows/pipe-wall-thickness.yaml) — pipe wall thickness workflow entry point

Node IDs (`B313-*`) are stable across the graph; folder paths use `nodes/{node_id}/` for direct lookup (Ctrl+P by id).

Nodes do not repeat the standard name in metadata; the parent pack folder defines the standard context.
