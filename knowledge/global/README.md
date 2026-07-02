# Global knowledge ontologies

Shared engineering ontologies used across all standard packs.

## Purpose

Cross-pack registries and graph node packs that are not tied to a single ASME/API/ASTM standard.

## Folders

| Folder | Was | Role |
|--------|-----|------|
| [materials/](materials/) | Global material registry (`registry.yaml`) and search catalog (`materials.db`) |
| [parameters/](parameters/) | Canonical engineering concepts (`PARAM-*`) referencing dimension nodes |
| [dimensions/](dimensions/) | Pipe NPS registry + physical dimension nodes (`DIM-*`) referencing unit nodes |
| [units/](units/) | Global unit graph (`UNIT-mm`, `UNIT-MPa`, …) and `derived_from` edges |
| [datatypes/](datatypes/) | *(new)* | Placeholder for future datatype ontology nodes |

## Entry Points

| File | Role |
|------|------|
| `materials/registry.yaml` | Material slug → ASTM table DB registry |
| `materials/supplemental.yaml` | Supplemental non-ASTM material entries |
| `dimensions/registry.yaml` | Pipe dimension source registry |
| `parameters/nodes/PARAM-*.yaml` | Canonical parameters (pressure, temperature, material, …) with `has_dimension` edges |
| `dimensions/nodes/DIM-*.yaml` | Physical dimensions (pressure, length, …) with `references` to unit nodes |
| `units/index.md` | Unit pack manifest |
| `units/nodes/UNIT-*.yaml` | Unit graph nodes (14 flat YAML files) |

## Dependencies

**Imports (runtime):** `engine/reference/knowledge_paths.py`, `engine/reference/material_catalog_db.py`, `engine/reference/pipe_dimensions_registry.py`, `engine/units/unit_resolver.py`.

**Imported by:** `engine/executor/material_properties_lookup.py`, `api/material_catalog.py`, validation/unit conversion, `scripts/build_material_catalog_db.py`.

## Runtime Usage

**Active:** `materials/`, `dimensions/`, and `units/` are on the execution path for material search, NPS lookup, and unit conversion.

**Forward-looking:** `parameters/` — canonical concept ontology; standards packs will migrate to reference `PARAM-*` nodes.

**Inactive:** `datatypes/` — empty placeholder only.

## Execution trace — materials

```
load_material_registry(standards_root)
  → knowledge/global/materials/registry.yaml
  → resolve table DBs under knowledge/standards/astm/
  → knowledge/global/materials/materials.db (search index)
```

## Execution trace — parameters and dimensions

```
Parameter node (PARAM-design-pressure)
  → has_dimension → DIM-pressure
Dimension node (DIM-pressure)
  → references → UNIT-Pa, UNIT-MPa, UNIT-psi, UNIT-bar
Unit nodes (UNIT-*)
  → dimension: pressure (string key matching DIM-* .key)
```

## Execution trace — pipe dimensions

```
PipeDimensionLookup(standards_root)
  → load_pipe_dimensions_registry()
  → knowledge/global/dimensions/registry.yaml
  → resolve_standard_pack → pack tables/*.yaml
  → pack/pipe_dimensions.db
```

## Execution trace — units

```
UnitResolver.default()
  → knowledge/global/units/
  → GraphBuilder / build_or_load_graph
  → derived_from edges for unit conversion
```
