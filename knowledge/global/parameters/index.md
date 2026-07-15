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
| `PARAM-internal-design-gage-pressure` | physical_quantity | `DIM-pressure` | [`CONCEPT-pressure`](../concepts/nodes/CONCEPT-pressure.yaml) |
| `PARAM-allowable-stress` | physical_quantity | `DIM-pressure` | [`CONCEPT-allowable-stress`](../concepts/nodes/CONCEPT-allowable-stress.yaml) |
| `PARAM-design-temperature` | environmental_condition | `DIM-temperature` | [`CONCEPT-temperature`](../concepts/nodes/CONCEPT-temperature.yaml) |
| `PARAM-corrosion-allowance` | geometric_quantity | `DIM-length` | [`CONCEPT-wall-thickness`](../concepts/nodes/CONCEPT-wall-thickness.yaml) |
| `PARAM-required-wall-thickness` | calculated_quantity | `DIM-length` | [`CONCEPT-wall-thickness`](../concepts/nodes/CONCEPT-wall-thickness.yaml) |
| `PARAM-minimum-required-thickness` | calculated_quantity | `DIM-length` | [`CONCEPT-wall-thickness`](../concepts/nodes/CONCEPT-wall-thickness.yaml) |
| `PARAM-outside-diameter` | geometric_quantity | `DIM-length` | [`CONCEPT-pipe-diameter`](../concepts/nodes/CONCEPT-pipe-diameter.yaml) |
| `PARAM-weld-strength-reduction-factor-w` | factor | `DIM-dimensionless` | [`CONCEPT-weld-joint-efficiency`](../concepts/nodes/CONCEPT-weld-joint-efficiency.yaml) |
| `PARAM-material-grade` | categorical | `DIM-material-designation` | [`CONCEPT-material`](../concepts/nodes/CONCEPT-material.yaml) |
| `PARAM-metallurgical-group` | selection | — | [`CONCEPT-material`](../concepts/nodes/CONCEPT-material.yaml) |
| `PARAM-pipe-construction-type` | selection | — | [`CONCEPT-pipe-construction`](../concepts/nodes/CONCEPT-pipe-construction.yaml) |
| `PARAM-basic-casting-quality-factor` | factor | `DIM-dimensionless` | — |
| `PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes` | factor | `DIM-dimensionless` | [`CONCEPT-weld-joint-efficiency`](../concepts/nodes/CONCEPT-weld-joint-efficiency.yaml) |
| `PARAM-temperature-coefficient-y` | coefficient | `DIM-dimensionless` | [`CONCEPT-temperature-coefficient`](../concepts/nodes/CONCEPT-temperature-coefficient.yaml) |
| `PARAM-nominal-pipe-size` | selection | — | [`CONCEPT-pipe-diameter`](../concepts/nodes/CONCEPT-pipe-diameter.yaml) |
| `PARAM-pressure-loading` | selection | — | [`CONCEPT-pressure`](../concepts/nodes/CONCEPT-pressure.yaml) |
| `PARAM-straight-pipe-section` | selection | — | — |
| `PARAM-pipe-schedule` | selection | — | [`CONCEPT-pipe-diameter`](../concepts/nodes/CONCEPT-pipe-diameter.yaml) |
| `PARAM-actual-wall-thickness` | geometric_quantity | `DIM-length` | [`CONCEPT-wall-thickness`](../concepts/nodes/CONCEPT-wall-thickness.yaml) |
| `PARAM-inside-diameter` | geometric_quantity | `DIM-length` | [`CONCEPT-pipe-diameter`](../concepts/nodes/CONCEPT-pipe-diameter.yaml) |
| `PARAM-external-design-pressure` | physical_quantity | `DIM-pressure` | [`CONCEPT-pressure`](../concepts/nodes/CONCEPT-pressure.yaml) |
| `PARAM-maximum-allowable-working-pressure` | calculated_quantity | `DIM-pressure` | [`CONCEPT-pressure`](../concepts/nodes/CONCEPT-pressure.yaml) |
| `PARAM-allowable-displacement-stress-range` | calculated_quantity | `DIM-pressure` | [`CONCEPT-stress`](../concepts/nodes/CONCEPT-stress.yaml) |
| `PARAM-stress-range-factor` | factor | `DIM-dimensionless` | [`CONCEPT-stress`](../concepts/nodes/CONCEPT-stress.yaml) |
| `PARAM-required-reinforcement-area` | calculated_quantity | — | — |
| `PARAM-run-excess-thickness-area` | calculated_quantity | — | — |
| `PARAM-excess-thickness-in-the-branch-pipe-wall` | calculated_quantity | — | — |

Parameter nodes define **contextual roles only** — no `value`, `unit`, `resolution`, or runtime state (see template forbidden fields). Composer UI hints live in `metadata` (`composer_input`, `composer_options`, `canonical_unit`, `default_value`) — see [`docs/rules.md`](../../../docs/rules.md) §17.

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

Authoring contract: [`audits/contracts/nodes/parameter.md`](../../../audits/contracts/nodes/parameter.md).

Runtime counterparts: values are Facts; objectives are Goals; both live in the per-task **Execution Context** ([`audits/contracts/runtime/execution-context.md`](../../../audits/contracts/runtime/execution-context.md), [`models/execution_context.py`](../../../models/execution_context.py)). **Authority Context** ([`audits/contracts/runtime/authority-context.md`](../../../audits/contracts/runtime/authority-context.md), [`models/authority_context.py`](../../../models/authority_context.py)) records which standards govern the execution — not as nodes under `knowledge/`.

## Compile

```bash
python scripts/build_graph_db.py --pack knowledge/global/parameters
```

Cross-pack edges (`introduced_by`, `used_by` → standards nodes) compile when the full graph is built; the parameters pack alone resolves `has_dimension` edges to `DIM-*` nodes in the dimensions pack.
