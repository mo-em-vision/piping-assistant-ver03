# engine/units/

Unit identification, registry of allowed units per dimension, and SI conversion for engineering inputs.

## Purpose

Bridge legacy unit strings (mm, psi, °F) to canonical `UNIT-*` graph node IDs and perform conversions via `UnitResolver` (graph-backed when cache available).

## Entry Points

| Symbol | File |
|--------|------|
| `get_unit_registry` | `unit_registry.py` |
| `get_unit_resolver`, `UnitResolver` | `unit_resolver.py` |
| `unit_id_from_legacy_symbol`, `symbol_from_unit_id` | `unit_ids.py` |

## Dependencies

**Depends on:** `engine/reference/graph_cache` (optional, for resolver), `engine/units/unit_ids.py`

**Used by:** `engine/executor/unit_manager.py`, `engine/state/workflow_parameters.py`, `engine/validation/unit_validator.py`, `engine/reference/parameter_metadata.py`

## Runtime Usage

**Active** during input validation, unit conversion before calculations, and workflow parameter display.

## Possible Dead Code

| Item | Confidence |
|------|------------|
| `units/__init__.py` empty exports | **Medium** — package surface unused; submodules imported directly |

## Notes

- `UnitRegistry` loads allowed units from graph unit nodes when registry is warmed.
- `UnitResolver` applies pure-scaling `factor` edges and evaluates `equation`-linked `converts_to` steps via sympy.
- `reset_unit_registry` / `reset_unit_resolver` exist for test isolation.

## Execution Traces

```
NodeRunner / unit_manager.prepare_engineering_input
  → unit_resolver.get_unit_resolver().convert(...)
  → (optional) graph_cache.build_or_load_graph for unit nodes

unit_validator.validate
  → unit_registry.get_unit_registry().allowed_units(dimension)
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Package marker (empty `__all__`) | — | — |
| `unit_ids.py` | Legacy symbol ↔ UNIT-* id | `unit_id_from_legacy_symbol`, `normalize_dimension` | unit_registry, unit_resolver, parameter_metadata |
| `unit_registry.py` | Dimension → allowed units | `UnitRegistry`, `get_unit_registry` | workflow_parameters, unit_validator |
| `unit_resolver.py` | Conversion engine | `UnitResolver`, `get_unit_resolver` | unit_manager, unit_validator, unit_registry |
