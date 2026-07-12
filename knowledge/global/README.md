# Global knowledge ontologies

Shared engineering ontologies used across all standard packs.

## Purpose

Cross-pack registries and graph node packs that are not tied to a single ASME/API/ASTM standard.

## Folders

| Folder | Was | Role |
|--------|-----|------|
| [materials/](materials/) | Global material registry (`registry.yaml`) and search catalog (`materials.db`) |
| [concepts/](concepts/) | Engineering concept ontology (`CONCEPT-*`) grouping semantic meaning |
| [authorities/](authorities/) | Authority ontology (`AUTH-*`) — canonical standards, codes, and specifications |
| [parameters/](parameters/) | Canonical parameter roles (`PARAM-*`) referencing dimension nodes |
| [dimensions/](dimensions/) | Pipe NPS registry + physical dimension nodes (`DIM-*`) with `allows_unit` edges |
| [units/](units/) | Global unit graph (`UNIT-mm`, `UNIT-MPa`, …) with `belongs_to_dimension` and `converts_to` edges |
| [datatypes/](datatypes/) | *(new)* | Placeholder for future datatype ontology nodes |

## Entry Points

| File | Role |
|------|------|
| `materials/registry.yaml` | Material slug → ASTM table DB registry |
| `materials/supplemental.yaml` | Supplemental non-ASTM material entries |
| `dimensions/registry.yaml` | Pipe dimension source registry |
| `concepts/nodes/CONCEPT-*.yaml` | Engineering concepts (pressure, wall thickness, material, …) with `has_parameter` edges |
| `authorities/nodes/AUTH-*.yaml` | Canonical authorities (ASME B31.3, ASTM A106, …) with `contains` / `table` edges |
| `parameters/nodes/PARAM-*.yaml` | Canonical parameters (design pressure, corrosion allowance, …) with `has_dimension` edges |
| `dimensions/nodes/DIM-*.yaml` | Physical dimensions (pressure, length, …) with `allows_unit` edges to unit nodes |
| `units/index.md` | Unit pack manifest |
| `units/nodes/UNIT-*.yaml` | Unit graph nodes (14 flat YAML files) |

## Dependencies

**Imports (runtime):** `engine/reference/knowledge_paths.py`, `engine/reference/material_catalog_db.py`, `engine/reference/pipe_dimensions_registry.py`, `engine/units/unit_resolver.py`.

**Imported by:** `engine/executor/material_properties_lookup.py`, `api/material_catalog.py`, validation/unit conversion, `scripts/build_material_catalog_db.py`.

## Runtime Usage

**Active:** `materials/`, `dimensions/`, and `units/` are on the execution path for material search, NPS lookup, and unit conversion.

**Forward-looking:** `concepts/` and `parameters/` — ontology layers; standards packs will migrate to reference `CONCEPT-*` and `PARAM-*` nodes.

**Runtime (not in this folder):** Facts, Goals, the unified **Execution Context**, and **Authority Context** live on each task — see [`models/execution_context.py`](../../models/execution_context.py), [`models/authority_context.py`](../../models/authority_context.py), [`models/fact.py`](../../models/fact.py), [`models/goal.py`](../../models/goal.py), and [`audits/contracts/runtime/execution-context.md`](../../audits/contracts/runtime/execution-context.md) / [`authority-context.md`](../../audits/contracts/runtime/authority-context.md). **Authority nodes** (`AUTH-*`) in [`authorities/`](authorities/) are immutable knowledge; Authority Context selects which are active. Do not add `knowledge/global/facts/` or `knowledge/global/goals/` packs.

**Inactive:** `datatypes/` — empty placeholder only.

## Execution trace — materials

```
load_material_registry(standards_root)
  → knowledge/global/materials/registry.yaml
  → resolve table DBs under knowledge/standards/astm/
  → knowledge/global/materials/materials.db (search index)
```

## Execution trace — authorities

```
AUTH-ASME-B31.3 (knowledge/global/authorities/)
  → contains → 304.1.1, B313-table-A-1 (asme_b31.3 standards pack)

AuthorityContext.active_authorities[].authority_id
  → AUTH-ASME-B31.3
```

## Execution trace — concepts, parameters, and dimensions

```
Concept node (CONCEPT-pressure)
  → has_parameter → PARAM-design-pressure
  → has_dimension → DIM-pressure
Parameter node (PARAM-design-pressure)
  → has_dimension → DIM-pressure
Dimension node (DIM-pressure)
  → allows_unit → UNIT-Pa, UNIT-MPa, UNIT-psi, UNIT-bar
Unit nodes (UNIT-*)
  → belongs_to_dimension → DIM-pressure
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
