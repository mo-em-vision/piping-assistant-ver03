"""System-resolved lookup, equation, and report requirements in engineering plan."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.legacy_goal_adapter import enrich_plan_requirements, finalize_engineering_plan
from engine.planner.plan_inspector import build_planner_inspector_summary
from engine.planner.plan_validation import validate_engineering_plan
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import requirement_key_for_class
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption

_LOOKUP_IDS = (
    "REQ-allowable_stress_lookup",
    "REQ-metallurgical_group_lookup",
    "REQ-temperature_coefficient_Y_lookup",
    "REQ-weld_joint_efficiency_lookup",
    "REQ-weld_strength_reduction_factor_W_lookup",
)

_EQUATION_IDS = (
    "REQ-required_wall_thickness",
    "REQ-minimum_required_thickness_eq",
)

_REPORT_ID = "REQ-calculation_report"

_LOOKUP_SOURCES = {
    "REQ-allowable_stress_lookup": "asme-b313-table-A-1",
    "REQ-metallurgical_group_lookup": "MAT-catalog",
    "REQ-temperature_coefficient_Y_lookup": "asme-b313-table-304-1-1-1",
    "REQ-weld_joint_efficiency_lookup": "asme-b313-table-A-2",
    "REQ-weld_strength_reduction_factor_W_lookup": "asme-b313-table-302-3-5-1",
}

_EQUATION_SOURCES = {
    "REQ-required_wall_thickness": "asme-b313-304-1-2-eq-3a",
    "REQ-minimum_required_thickness_eq": "asme-b313-304-1-1-eq-2",
}


def _gates_satisfied_task():
    manager = TaskStateManager()
    task = manager.create_task("system-reqs-pwt", status=TaskStatus.AWAITING_INPUT)
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
    return manager.get_task(task.task_id)


def test_plan_includes_lookup_equation_and_report_requirements() -> None:
    task = _gates_satisfied_task()
    plan = finalize_engineering_plan(build_pipe_wall_engineering_plan(task))
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    for req_id in (*_LOOKUP_IDS, *_EQUATION_IDS, _REPORT_ID):
        assert req_id in plan.requirements, req_id

    for req_id in _LOOKUP_IDS:
        req = plan.requirements[req_id]
        assert req.requirement_class == "table_lookup"
        assert req.status == "blocked"
        assert req.question_spec is None
        assert req.resolution is not None
        assert req.resolution["method"] == "lookup"
        assert req.resolution["source_node_id"] == _LOOKUP_SOURCES[req_id]
        assert req.key == requirement_key_for_class("table_lookup", req.field)

    for req_id in _EQUATION_IDS:
        req = plan.requirements[req_id]
        assert req.requirement_class == "equation_result"
        assert req.status == "blocked"
        assert req.question_spec is None
        assert req.resolution["method"] == "equation"
        assert req.resolution["source_node_id"] == _EQUATION_SOURCES[req_id]
        assert req.key == requirement_key_for_class("equation_result", req.field)
        assert req.key.startswith("equation-")

    report = plan.requirements[_REPORT_ID]
    assert report.requirement_class == "report_output"
    assert report.status == "blocked"
    assert report.question_spec is None
    assert report.phase == "reporting"
    assert report.depends_on == ["REQ-minimum_required_thickness_eq"]
    assert report.resolution == {"method": "report", "output_field": "calculation_report"}
    assert report.key == "report-calculation_report"


def test_allowable_stress_lookup_shape_matches_canonical_contract() -> None:
    task = _gates_satisfied_task()
    plan = build_pipe_wall_engineering_plan(task)
    enrich_plan_requirements(plan.requirements)
    req = plan.requirements["REQ-allowable_stress_lookup"]

    assert req.id == "REQ-allowable_stress_lookup"
    assert req.key == "lookup-allowable_stress"
    assert req.field == "allowable_stress"
    assert req.title == "Allowable Stress"
    assert req.parameter_node_id == "PARAM-allowable-stress"
    assert req.phase == "coefficient_resolution"
    assert req.required_by == ["GOAL-calculate-minimum-required-thickness"]
    assert req.depends_on == ["REQ-material_grade", "REQ-design_temperature"]
    assert req.resolution == {
        "method": "lookup",
        "source_node_id": "asme-b313-table-A-1",
        "output_field": "allowable_stress",
    }


def test_system_resolved_requirements_visible_in_planner_inspector() -> None:
    task = _gates_satisfied_task()
    plan = finalize_engineering_plan(build_pipe_wall_engineering_plan(task))
    summary = build_planner_inspector_summary(plan)

    system_ids = {item["id"] for item in summary["system_resolved_requirements"]}
    for req_id in (*_LOOKUP_IDS, *_EQUATION_IDS, _REPORT_ID):
        assert req_id in system_ids

    lookup_summary = {
        item["id"]: item for item in summary["derived_or_lookup_values"] if "id" in item
    }
    for req_id in _LOOKUP_IDS:
        assert req_id in lookup_summary
        assert lookup_summary[req_id]["source_node_id"] == _LOOKUP_SOURCES[req_id]

    classes = {item["requirement_class"] for item in summary["system_resolved_requirements"]}
    assert "table_lookup" in classes
    assert "equation_result" in classes
    assert "report_output" in classes


def test_fresh_plan_includes_conditional_system_requirements() -> None:
    manager = TaskStateManager()
    task = manager.create_task("system-reqs-fresh", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    plan = finalize_engineering_plan(build_pipe_wall_engineering_plan(task))

    for req_id in (*_LOOKUP_IDS, *_EQUATION_IDS, _REPORT_ID):
        assert req_id in plan.requirements
        assert plan.requirements[req_id].activation_status == "conditional"
