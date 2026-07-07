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


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("normalized-fresh-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


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
    assert plan.input_strategy.current_phase == "expansion_assumptions"
    assert plan.input_strategy.next_fields == ["straight_pipe_section"]
    assert len(plan.input_strategy.next_fields) <= 1

    assert plan.traversal is not None
    assert plan.traversal.current_active_node_id == param_node_id_for_input("straight_pipe_section")
    assert plan.traversal.current_active_node is not None
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
