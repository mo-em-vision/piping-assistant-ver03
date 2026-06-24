# ASME B36.10M — Welded and Seamless Wrought Steel Pipe

This pack provides **pipe dimension lookup tables** for engineering workflows that need nominal pipe size (NPS), outside diameter, and schedule wall thickness.

> Development sample data aligned with ASME B36.10M table structure. Verify against the licensed standard for production use.

## Layout

```
asme_b36.10/
  index.md
  readme.md
  pipe_dimensions.db          # built from YAML (see below)
  tables/
    welded_seamless_pipe_dimensions.yaml
```

## Build database

```bash
python scripts/build_pipe_dimensions_db.py
```

Sources are registered in `standards/pipe_dimensions/registry.yaml`. To add another standard later, add its pack YAML there and rerun the build script.

## Related standards

- **ASME B31.3** — uses outside diameter `D` in wall thickness formulas (`standards/asme/asme_b31.3/`)
