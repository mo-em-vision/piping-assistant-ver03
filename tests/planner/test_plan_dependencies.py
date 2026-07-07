"""Central engineering_plan.dependencies graph."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.legacy_goal_adapter import finalize_engineering_plan
from engine.planner.plan_dependencies import build_plan_dependencies
from engine.planner.plan_validation import validate_engineering_plan
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus

_EXPECTED_PIPE_WALL_EDGES = {
    ("REQ-material_grade", "REQ-allowable_stress_lookup", "lookup_input"),
    ("REQ-design_temperature", "REQ-allowable_stress_lookup", "lookup_input"),
    ("REQ-material_grade", "REQ-metallurgical_group_lookup", "lookup_input"),
    ("REQ-metallurgical_group_lookup", "REQ-temperature_coefficient_Y_lookup", "lookup_input"),
    ("REQ-design_temperature", "REQ-temperature_coefficient_Y_lookup", "lookup_input"),
    ("REQ-pipe_construction_type", "REQ-weld_joint_efficiency_lookup", "lookup_input"),
    ("REQ-material_grade", "REQ-weld_strength_reduction_factor_W_lookup", "lookup_input"),
    ("REQ-design_temperature", "REQ-weld_strength_reduction_factor_W_lookup", "lookup_input"),
    ("REQ-internal_design_gage_pressure", "REQ-required_wall_thickness", "equation_input"),
    ("REQ-diameter_resolution", "REQ-required_wall_thickness", "equation_input"),
    ("REQ-allowable_stress_lookup", "REQ-required_wall_thickness", "equation_input"),
    ("REQ-weld_joint_efficiency_lookup", "REQ-required_wall_thickness", "equation_input"),
    ("REQ-temperature_coefficient_Y_lookup", "REQ-required_wall_thickness", "equation_input"),
    ("REQ-weld_strength_reduction_factor_W_lookup", "REQ-required_wall_thickness", "equation_input"),
    ("REQ-required_wall_thickness", "REQ-minimum_required_thickness_eq", "equation_input"),
    ("REQ-corrosion_allowance", "REQ-minimum_required_thickness_eq", "equation_input"),
    ("REQ-minimum_required_thickness_eq", "REQ-calculation_report", "requires"),
    ("REQ-nominal_pipe_size", "REQ-outside_diameter_lookup", "lookup_input"),
    ("REQ-outside_diameter_lookup", "REQ-diameter_resolution", "resolves"),
    ("ALT-nps-lookup", "REQ-nominal_pipe_size", "activates"),
}


def _fresh_task():
    manager = TaskStateManager()
    task = manager.create_task("plan-deps", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    return task


def test_build_plan_dependencies_matches_pipe_wall_contract() -> None:
    task = _fresh_task()
    plan = finalize_engineering_plan(build_pipe_wall_engineering_plan(task))
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    assert len(plan.dependencies) > 0
    edges = {(edge.from_id, edge.to_id, edge.type) for edge in plan.dependencies}
    assert edges == _EXPECTED_PIPE_WALL_EDGES


def test_canonical_requirements_have_no_edges_field() -> None:
    task = _fresh_task()
    plan = finalize_engineering_plan(build_pipe_wall_engineering_plan(task))

    for req_id, req in plan.requirements.items():
        payload = req.to_dict()
        assert "edges" not in payload, req_id

    plan_dict = plan.to_dict()
    for req_id, req_payload in plan_dict["requirements"].items():
        assert "edges" not in req_payload, req_id


def test_legacy_goal_map_includes_dependency_edges() -> None:
    task = _fresh_task()
    plan = finalize_engineering_plan(build_pipe_wall_engineering_plan(task))
    assert plan.legacy_goal_map is not None

    legacy = plan.legacy_goal_map["REQ-material_grade"]
    assert legacy["edges"]
    assert {
        "from": "REQ-material_grade",
        "to": "REQ-allowable_stress_lookup",
        "type": "lookup_input",
    } in legacy["edges"]

    lookup = plan.legacy_goal_map["REQ-allowable_stress_lookup"]
    assert {
        "from": "REQ-allowable_stress_lookup",
        "to": "REQ-required_wall_thickness",
        "type": "equation_input",
    } in lookup["edges"]


def test_lookup_and_equation_requirements_have_incoming_edges() -> None:
    task = _fresh_task()
    plan = finalize_engineering_plan(build_pipe_wall_engineering_plan(task))
    incoming = {(edge.to_id, edge.type) for edge in plan.dependencies}

    for req_id in (
        "REQ-allowable_stress_lookup",
        "REQ-metallurgical_group_lookup",
        "REQ-temperature_coefficient_Y_lookup",
        "REQ-weld_joint_efficiency_lookup",
        "REQ-weld_strength_reduction_factor_W_lookup",
    ):
        assert (req_id, "lookup_input") in incoming

    for req_id in ("REQ-required_wall_thickness", "REQ-minimum_required_thickness_eq"):
        assert (req_id, "equation_input") in incoming

    assert ("REQ-calculation_report", "requires") in incoming


def test_build_plan_dependencies_from_requirements_only() -> None:
    from engine.planner.pipe_wall_plan import PIPE_WALL_WORKFLOW, build_pipe_wall_requirements
    from tests.helpers.goals import PIPE_WALL_ROOT_GOAL_ID

    requirements = build_pipe_wall_requirements(root_goal_id=PIPE_WALL_ROOT_GOAL_ID)
    edges = build_plan_dependencies(requirements, workflow_id=PIPE_WALL_WORKFLOW)
    assert len(edges) == len(_EXPECTED_PIPE_WALL_EDGES)
