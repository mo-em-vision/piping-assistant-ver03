"""Fresh pipe_wall_thickness_design normalized EngineeringPlan acceptance tests."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.plan_validation import (
    validate_engineering_plan,
    validate_engineering_plan_dict,
)
from engine.reference.parameter_keys import param_node_id_for_input
from engine.state.goal_projection import goals_to_api_dict
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus

_CANONICAL_PLAN_KEYS = (
    "plan_id",
    "task_id",
    "workflow_id",
    "root_goal",
    "requirements",
    "dependencies",
    "input_strategy",
    "phases",
    "graph",
    "traversal",
)

_REQUIRED_ROOT_OUTPUTS = (
    "minimum_required_thickness",
    "required_wall_thickness",
    "calculation_report",
)


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("normalized-fresh-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def test_fresh_pipe_wall_canonical_plan_contract() -> None:
    """Fresh initiation must return nested EngineeringPlan, not a flat GOAL/REQ map."""
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    assert plan.plan_id
    assert plan.plan_id.startswith("PLAN-")
    assert plan.task_id == task.task_id
    assert plan.workflow_id == "pipe_wall_thickness_design"

    assert plan.root_goal is not None
    assert plan.requirements
    assert plan.dependencies
    assert plan.input_strategy is not None
    assert plan.phases
    assert plan.graph is not None
    assert plan.traversal is not None

    assert plan.root_goal.id == "GOAL-calculate-minimum-required-thickness"
    assert plan.root_goal.target_parameter == "PARAM-minimum-required-thickness"
    assert plan.root_goal.target_field == "minimum_required_thickness"
    assert list(plan.root_goal.required_outputs) == list(_REQUIRED_ROOT_OUTPUTS)

    serialized = plan.to_dict()
    for key in _CANONICAL_PLAN_KEYS:
        assert key in serialized, f"missing canonical key: {key}"

    flat_goal_keys = [key for key in serialized if str(key).startswith(("GOAL-", "REQ-"))]
    assert flat_goal_keys == []

    assert plan.legacy_goal_map is not None
    assert "legacy_goal_map" in serialized
    legacy = serialized["legacy_goal_map"]
    assert isinstance(legacy, dict)
    assert "GOAL-calculate-minimum-required-thickness" in legacy
    assert legacy is not serialized
    assert legacy is not serialized["requirements"]

    dict_validation = validate_engineering_plan_dict(serialized)
    assert dict_validation.valid, dict_validation.errors


def test_fresh_pipe_wall_normalized_engineering_plan() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors

    assert plan.root_goal.id == "GOAL-calculate-minimum-required-thickness"
    assert plan.root_goal.target_field == "minimum_required_thickness"
    assert plan.root_goal.blocked_by == [
        "REQ-straight_pipe_section",
        "REQ-pressure_loading",
    ]

    diameter = plan.requirements["REQ-diameter_resolution"]
    assert diameter.alternatives is not None
    assert len(diameter.alternatives) == 2
    alt_ids = {alt.id for alt in diameter.alternatives}
    assert "ALT-direct-outside-diameter" in alt_ids
    assert "ALT-nps-lookup" in alt_ids

    assert len(plan.dependencies) > 0
    assert plan.input_strategy is not None
    assert plan.input_strategy.mode == "single_next_question"
    assert plan.input_strategy.current_phase == "expansion_assumptions"
    assert plan.input_strategy.next_fields == ["straight_pipe_section"]
    assert "pressure_loading" not in plan.input_strategy.next_fields
    assert "pressure_loading" in plan.input_strategy.blocked_fields

    active_phases = [phase for phase in plan.phases if phase.status == "active"]
    assert len(active_phases) == 1
    assert active_phases[0].id == "expansion_assumptions"

    assert plan.traversal is not None
    straight_param = param_node_id_for_input("straight_pipe_section")
    assert plan.traversal.current_active_node_id == straight_param
    assert plan.traversal.current_active_node is not None
    assert plan.traversal.current_active_node.node_id == straight_param
    assert len(plan.traversal.pending_expansion_nodes) > 0
    assert len(plan.traversal.expanded_nodes) > 0
    assert plan.traversal.branch_decisions

    pending_ids = {item.node_id for item in plan.traversal.pending_expansion_nodes}
    expanded_ids = {item.node_id for item in plan.traversal.expanded_nodes}
    assert pending_ids.isdisjoint(expanded_ids)

    internal_pressure = plan.requirements["REQ-internal_design_gage_pressure"]
    assert internal_pressure.activation_status == "conditional"

    for lookup_id in (
        "REQ-allowable_stress_lookup",
        "REQ-weld_joint_efficiency_lookup",
        "REQ-temperature_coefficient_Y_lookup",
        "REQ-weld_strength_reduction_factor_W_lookup",
        "REQ-metallurgical_group_lookup",
    ):
        assert lookup_id in plan.requirements

    for equation_id in ("REQ-required_wall_thickness", "REQ-minimum_required_thickness_eq"):
        assert equation_id in plan.requirements

    serialized = plan.to_dict()
    dict_validation = validate_engineering_plan_dict(serialized)
    assert dict_validation.valid, dict_validation.errors
    assert "GOAL-calculate-minimum-required-thickness" not in serialized
    assert "REQ-straight_pipe_section" in serialized["requirements"]


def test_flat_legacy_goal_map_fails_canonical_validation() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    flat_legacy = dict(plan.legacy_goal_map or {})

    result = validate_engineering_plan_dict(flat_legacy)
    assert not result.valid
    assert any("flat top-level GOAL-*/REQ-* map" in error for error in result.errors)


def test_goal_store_projection_is_not_canonical_engineering_plan() -> None:
    from engine.planner.goal_builder import build_goal_tree
    from pathlib import Path
    from engine.reference.standards_reader import StandardsReader

    manager, task = _fresh_pipe_wall_task()
    reader = StandardsReader(
        Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    build_goal_tree(task, reader)
    legacy = goals_to_api_dict(task)

    result = validate_engineering_plan_dict(legacy)
    assert not result.valid
    assert "GOAL-calculate-minimum-required-thickness" in legacy
    assert "requirements" not in legacy
