# Pipe wall thickness — planner acceptance contract

Workflow-specific acceptance criteria for `pipe_wall_thickness_design`. General planner invariants live in [`docs/rules.md`](../../rules.md) §19–§20. This file holds identifiers, phase expectations, and test inventories that change with the workflow — not permanent architecture rules.

**Workflow id:** `pipe_wall_thickness_design`  
**Root goal:** `GOAL-calculate-minimum-required-thickness`  
**Target parameter:** `PARAM-minimum-required-thickness` / field `minimum_required_thickness`  
**Required root outputs:** `minimum_required_thickness`, `required_wall_thickness`, `calculation_report`

---

## Fresh initiation (`expansion_assumptions`)

On a new task with no confirmed inputs:

| Check | Expected |
| --- | --- |
| `input_strategy.mode` | `single_next_question` |
| `input_strategy.current_phase` | `expansion_assumptions` |
| `input_strategy.next_fields` | `["straight_pipe_section"]` only |
| `input_strategy.blocked_fields` | includes `pressure_design_case`; does **not** include it in `next_fields` |
| Active phases | exactly one: `expansion_assumptions` |
| Root `blocked_by` | `REQ-straight_pipe_section`, `REQ-pressure_design_case` (gate requirements only) |
| `traversal.current_active_node_id` | gatherable PARAM for `straight_pipe_section` |
| `traversal.pending_expansion_nodes` ∩ `traversal.expanded_nodes` | empty |
| Internal pressure requirement | `REQ-internal_design_gage_pressure` has `activation_status: conditional` |

After `straight_pipe_section` is confirmed, expect hard-block only on `REQ-pressure_design_case`, `next_fields == ["pressure_design_case"]`, and phase `path_decisions`.

---

## Diameter resolution

| Check | Expected |
| --- | --- |
| Requirement | `REQ-diameter_resolution` |
| Alternatives | exactly two: `ALT-direct-outside-diameter`, `ALT-nps-lookup` |
| Root blocking | must **not** hard-block on both `REQ-outside_diameter` and `REQ-nominal_pipe_size` |
| NPS path | `REQ-outside_diameter_lookup` uses `table_lookup` when present |
| Dependency rule | `REQ-diameter_resolution` must not be a `lookup_input` source for outside-diameter lookup |

---

## Lookup and equation requirements

Lookup requirements (S, Y, E, W, metallurgical group) must be present on the fresh normalized plan:

| Requirement id | Source node (reference) |
| --- | --- |
| `REQ-allowable_stress` | `asme-b313-table-A-1` |
| `REQ-metallurgical_group` | `MAT-catalog` |
| `REQ-temperature_coefficient_Y` | `asme-b313-table-304-1-1-1` |
| `REQ-weld_joint_efficiency` | `asme-b313-table-A-2` |
| `REQ-weld_joint_strength_reduction_factor_W` | `asme-b313-table-302-3-5-1` |

Equation requirements:

| Requirement id | Source equation |
| --- | --- |
| `REQ-required_wall_thickness` | `asme-b313-304-1-2-eq-3a` |
| `REQ-minimum_required_thickness_eq` | `asme-b313-304-1-1-eq-2` |

Shared constants for tests: `tests/planner/plan_contract.py` (`PIPE_WALL_LOOKUP_IDS`, `PIPE_WALL_CONTRACT_REQUIREMENT_IDS`, `LOOKUP_SOURCES`, `EQUATION_SOURCES`).

---

## Validation entry point

Pipe-wall plan validation runs in `build_pipe_wall_engineering_plan()` **after** `finalize_engineering_plan()` (dependencies populated). Failures surface on `plan.debug.validation_errors` / `validation_warnings` and in the Planner dev tab.

---

## Test inventory

| Test file | Role |
| --- | --- |
| `tests/planner/test_fresh_pipe_wall_normalized_plan.py` | Fresh initiation acceptance; canonical vs flat legacy map |
| `tests/planner/test_plan_validation.py` | Dependency and diameter invariants |
| `tests/planner/test_plan_requirements.py` | Graph-derived requirement presence |
| `tests/planner/test_graph_navigation.py` | Fresh pipe-wall graph navigation from plan |
| `tests/planner/plan_contract.py` | Shared requirement id constants |

General (non-workflow) planner tests remain cited in [`docs/rules.md`](../../rules.md) §19–§20.
