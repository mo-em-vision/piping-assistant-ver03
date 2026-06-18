# ASME B31.3 Standard Pack

Self-contained engineering knowledge for ASME B31.3 Process Piping.

## Layout

```
asme_b31.3/
├── index.md          # navigation links only
├── readme.md
├── roots/            # user-level analysis entry points
├── nodes/            # paragraph / calculation knowledge units
├── templates/
├── tables/
├── figures/
└── reports/
```

## Sample implementation

The first sample node follows `docs/core/7. node_structure_design.md` and `docs/core/8. Node Template.md`:

- `nodes/B313-304.1.1/` — wall thickness calculation (`t = PD / 2(SEW + PY)`)
- `roots/pipe_wall_thickness_design/` — workflow entry point aligned with `pipe_wall_thickness_design` router classification

Nodes do not repeat the standard name in metadata; the parent folder defines the standard context.
