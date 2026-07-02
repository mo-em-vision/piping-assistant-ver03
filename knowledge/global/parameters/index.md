# Global parameter ontology

Canonical parameter roles (`PARAM-*`) shared across all standards packs.

## Purpose

Parameter nodes define **contextual engineering roles** — not values, units, resolution strategy, or runtime state. Semantic meaning lives in [`../concepts/`](../concepts/) (`CONCEPT-*`); values belong to Facts in the Execution Context.

## Layout

| Path | Role |
|------|------|
| [nodes/](nodes/) | Canonical parameter ontology (`PARAM-*.yaml`) |

## Canonical parameters

| Node | Class | Dimension | Concept |
|------|-------|-----------|---------|
| `PARAM-design-pressure` | physical_quantity | `DIM-pressure` | [`CONCEPT-pressure`](../concepts/nodes/CONCEPT-pressure.yaml) |
| `PARAM-allowable-stress` | physical_quantity | `DIM-pressure` | [`CONCEPT-allowable-stress`](../concepts/nodes/CONCEPT-allowable-stress.yaml) |
| `PARAM-design-temperature` | environmental_condition | `DIM-temperature` | [`CONCEPT-temperature`](../concepts/nodes/CONCEPT-temperature.yaml) |
| `PARAM-corrosion-allowance` | geometric_quantity | `DIM-length` | [`CONCEPT-wall-thickness`](../concepts/nodes/CONCEPT-wall-thickness.yaml) |
| `PARAM-material-specification` | material_designation | `DIM-material-designation` | [`CONCEPT-material`](../concepts/nodes/CONCEPT-material.yaml) |

Parameter nodes define **contextual roles only** — no `value`, `unit`, `resolution`, or runtime state (see template forbidden fields).

## Four-layer model

```
CONCEPT-*  ──has_parameter──►  PARAM-*  ──has_dimension──►  DIM-*  ──allows_unit──►  UNIT-*
```

| Layer | Pack | Defines |
|-------|------|---------|
| Concept | [`../concepts/`](../concepts/) | Semantic engineering meaning |
| Parameter | `parameters/` | Contextual role (design pressure, corrosion allowance, …) |
| Dimension | [`../dimensions/`](../dimensions/) | Compatible units for a quantity kind |
| Unit | [`../units/`](../units/) | Conversion between unit symbols |

Authoring template: [`docs/node-templates/Parameter Node.md`](../../../docs/node-templates/Parameter%20Node.md).

Runtime counterparts: values are Facts; objectives are Goals; both live in the per-task **Execution Context** ([`docs/node-templates/Execution Context.md`](../../../docs/node-templates/Execution%20Context.md), [`models/execution_context.py`](../../../models/execution_context.py)). **Authority Context** ([`docs/node-templates/Authority Context.md`](../../../docs/node-templates/Authority%20Context.md), [`models/authority_context.py`](../../../models/authority_context.py)) records which standards govern the execution — not as nodes under `knowledge/`.

## Compile

```bash
python scripts/build_graph_db.py --pack knowledge/global/parameters
```

Cross-pack edges (`introduced_by`, `used_by` → standards nodes) compile when the full graph is built; the parameters pack alone resolves `has_dimension` edges to `DIM-*` nodes in the dimensions pack.
