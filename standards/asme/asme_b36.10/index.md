# ASME B36.10M — Master Index

Reference tables for welded and seamless wrought steel pipe dimensions.

## Tables

| Table | Description |
|-------|-------------|
| [tables/welded_seamless_pipe_dimensions.yaml](tables/welded_seamless_pipe_dimensions.yaml) | Nominal pipe size (NPS), outside diameter, and schedule wall thickness |

## Usage

Lookup via `PipeDimensionLookup` (`engine/executor/pipe_dimension_lookup.py`):

- Keys: `nominal_pipe_size`, optional `schedule` (e.g. `40`, `80`, `STD`, `XS`)
- Outside diameter is constant for a given NPS regardless of schedule
