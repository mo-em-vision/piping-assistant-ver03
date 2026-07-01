# ASME B36.10M — Master Index

Reference tables for welded and seamless wrought steel pipe dimensions.

## Tables

| Table | Description |
|-------|-------------|
| [tables/B3610-table-2-1.yaml](tables/B3610-table-2-1.yaml) | Table 2-1 — Dimensions and Weights (Masses) of Welded and Seamless Wrought Steel Pipe |
| `pipe_dimensions.db` | SQLite lookup table (run `python scripts/build_pipe_dimensions_db.py`) |

## Usage

Lookup via `PipeDimensionLookup` (`engine/executor/pipe_dimension_lookup.py`), backed by `pipe_dimensions.db` when built:

- Keys: `nominal_pipe_size`, optional `schedule` (e.g. `40`, `80`, `STD`, `XS`)
- Outside diameter is constant for a given NPS regardless of schedule
