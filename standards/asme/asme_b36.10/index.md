# ASME B36.10M — Master Index

Reference tables for welded and seamless wrought steel pipe dimensions.

## Tables

| Table | Description |
|-------|-------------|
| [tables/welded_seamless_pipe_dimensions.yaml](tables/welded_seamless_pipe_dimensions.yaml) | Source YAML for NPS, outside diameter, and schedule wall thickness |
| `pipe_dimensions.db` | SQLite lookup table (run `python scripts/build_pipe_dimensions_db.py`) |

## Usage

Lookup via `PipeDimensionLookup` (`engine/executor/pipe_dimension_lookup.py`), backed by `pipe_dimensions.db` when built:

- Keys: `nominal_pipe_size`, optional `schedule` (e.g. `40`, `80`, `STD`, `XS`)
- Outside diameter is constant for a given NPS regardless of schedule
