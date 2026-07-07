"""Canonical PlanRequirement shape (no legacy goal fields)."""

from __future__ import annotations

from pathlib import Path

from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.goal_builder import build_goal_tree
from engine.planner.legacy_goal_adapter import enrich_plan_requirements
from engine.planner.plan_validation import validate_engineering_plan
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import LEGACY_REQUIREMENT_FIELD_NAMES, requirement_key_for_class
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption

_LEGACY_GOAL_KEYS = LEGACY_REQUIREMENT_FIELD_NAMES | {
    "goal_class",
    "satisfaction",
    "state",
    "metadata",
    "edges",
}


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _gates_satisfied_task():
    manager = TaskStateManager()
    task = manager.create_task("req-shape-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    from engine.state.fact_migration import fact_from_engineering_input

    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    return manager, manager.get_task(task.task_id)


def test_initial_internal_pressure_requirement_is_missing_not_ready() -> None:
    _, task = _gates_satisfied_task()
    reader = _reader()
    graph = GraphTools(reader)
    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.fact_store.active_facts()),
    )
    plan = build_pipe_wall_engineering_plan(task, preview=preview)
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    internal = plan.requirements["REQ-internal_design_gage_pressure"]
    assert internal.status == "missing"
    assert internal.requirement_class == "user_input"
    assert internal.activation_status == "active"


def test_pressure_loading_is_branch_decision_with_select_key() -> None:
    _, task = _gates_satisfied_task()
    plan = build_pipe_wall_engineering_plan(task)
    pressure = plan.requirements["REQ-pressure_loading"]
    assert pressure.requirement_class == "branch_decision"
    assert pressure.key == requirement_key_for_class("branch_decision", "pressure_loading")
    assert pressure.key == "select-pressure_loading"


def test_diameter_resolution_has_top_level_alternatives_and_question_spec() -> None:
    _, task = _gates_satisfied_task()
    plan = build_pipe_wall_engineering_plan(task)
    diameter = plan.requirements["REQ-diameter_resolution"]
    assert diameter.alternatives
    assert len(diameter.alternatives) == 2
    assert diameter.question_spec is not None
    assert diameter.question_spec.field == "diameter_input_mode"

    by_id = {alt.id: alt for alt in diameter.alternatives}
    direct = by_id["ALT-direct-outside-diameter"]
    assert direct.fields == ["outside_diameter"]
    assert direct.resolves == "outside_diameter"
    assert direct.method == "direct_input"

    nps = by_id["ALT-nps-lookup"]
    assert nps.fields == ["nominal_pipe_size"]
    assert nps.resolves == "outside_diameter"
    assert nps.method == "lookup"

    payload = diameter.to_dict()
    assert "alternatives" in payload
    assert "question_spec" in payload
    assert "metadata" not in payload
    assert "satisfaction" not in payload
    assert "goal_class" not in payload


def test_canonical_requirements_exclude_legacy_goal_fields() -> None:
    _, task = _gates_satisfied_task()
    plan = build_pipe_wall_engineering_plan(task)
    for req_id, req in plan.requirements.items():
        payload = req.to_dict()
        overlap = _LEGACY_GOAL_KEYS.intersection(payload.keys())
        assert not overlap, f"{req_id} leaked legacy fields: {sorted(overlap)}"


def test_internal_design_gage_pressure_normalized_mapping() -> None:
    _, task = _gates_satisfied_task()
    plan = build_pipe_wall_engineering_plan(task)
    req = plan.requirements["REQ-internal_design_gage_pressure"]
    enrich_plan_requirements(plan.requirements)

    assert req.id == "REQ-internal_design_gage_pressure"
    assert req.key == "input-internal_design_gage_pressure"
    assert req.field == "internal_design_gage_pressure"
    assert req.title
    assert req.parameter_node_id == "PARAM-internal-design-gage-pressure"
    assert req.phase == "parameter_gathering"
    assert req.required_by == ["GOAL-calculate-minimum-required-thickness"]
    assert req.depends_on == []
    assert req.question_spec is not None
    assert req.resolution == {
        "method": "user_input",
        "output_field": "internal_design_gage_pressure",
    }

    stored = plan.to_dict()["requirements"]["REQ-internal_design_gage_pressure"]
    assert stored["status"] == "missing"
    assert "metadata" not in stored


def test_legacy_goal_map_is_separate_from_canonical_requirements() -> None:
    manager, task = _gates_satisfied_task()
    reader = _reader()
    build_goal_tree(task, reader)
    manager.replace_task(task.task_id, task)

    plan_dict = task.outputs["engineering_plan"]
    internal = plan_dict["requirements"]["REQ-internal_design_gage_pressure"]
    legacy = plan_dict["legacy_goal_map"]["REQ-internal_design_gage_pressure"]

    assert "goal_class" in legacy
    assert "satisfaction" in legacy
    assert "goal_class" not in internal
    assert "satisfaction" not in internal
