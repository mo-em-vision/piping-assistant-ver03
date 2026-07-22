"""System-resolved lookup, equation, and report requirements in engineering plan."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.legacy_goal_adapter import enrich_plan_requirements, finalize_engineering_plan
from engine.planner.plan_inspector import build_planner_inspector_summary
from engine.planner.plan_validation import validate_engineering_plan
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import requirement_key_for_class
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.planner.helpers import _reader
from tests.planner.plan_contract import (
    EQUATION_SOURCES,
    LOOKUP_SOURCES,
    PIPE_WALL_LOOKUP_IDS,
    REQ_MINIMUM_REQUIRED_THICKNESS_EQ,
    REQ_REQUIRED_WALL_THICKNESS,
)

_LOOKUP_IDS = PIPE_WALL_LOOKUP_IDS
_EQUATION_IDS = (REQ_REQUIRED_WALL_THICKNESS, REQ_MINIMUM_REQUIRED_THICKNESS_EQ)
_REPORT_ID = "REQ-calculation_report"

_LOOKUP_RESOLUTION_METHODS = frozenset({"lookup", "material_catalog", "table_lookup"})

_LOOKUP_SOURCES = LOOKUP_SOURCES
_EQUATION_SOURCES = EQUATION_SOURCES


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
    plan = finalize_engineering_plan(build_engineering_plan(task, _reader()))
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
        assert req.resolution["method"] in _LOOKUP_RESOLUTION_METHODS
        source_node_id = req.resolution.get("source_node_id")
        if source_node_id is not None:
            assert source_node_id == _LOOKUP_SOURCES[req_id]
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
    assert report.depends_on == [REQ_REQUIRED_WALL_THICKNESS]
    assert report.resolution == {"method": "report", "output_field": "calculation_report"}
    assert report.key == "report-calculation_report"


def test_allowable_stress_lookup_shape_matches_canonical_contract() -> None:
    task = _gates_satisfied_task()
    plan = build_engineering_plan(task, _reader())
    enrich_plan_requirements(plan.requirements)
    req = plan.requirements["REQ-allowable_stress_lookup"]

    assert req.id == "REQ-allowable_stress_lookup"
    assert req.key == "lookup-allowable_stress"
    assert req.field == "allowable_stress"
    assert req.title == "Allowable Stress"
    assert req.parameter_node_id == "PARAM-allowable-stress"
    assert req.phase == "coefficient_resolution"
    assert req.required_by == ["GOAL-calculate-minimum-required-thickness"]
    assert req.depends_on == ["REQ-design_temperature", "REQ-material_grade"]
    assert req.resolution["method"] == "lookup"
    assert req.resolution["source_node_id"] == "asme-b313-table-A-1"
    assert req.resolution["output_field"] == "allowable_stress"


def test_system_resolved_requirements_visible_in_planner_inspector() -> None:
    task = _gates_satisfied_task()
    plan = finalize_engineering_plan(build_engineering_plan(task, _reader()))
    summary = build_planner_inspector_summary(plan)

    system_ids = {item["id"] for item in summary["system_resolved_requirements"]}
    for req_id in (*_LOOKUP_IDS, *_EQUATION_IDS, _REPORT_ID):
        assert req_id in system_ids

    lookup_summary = {
        item["id"]: item for item in summary["derived_or_lookup_values"] if "id" in item
    }
    for req_id in _LOOKUP_IDS:
        assert req_id in lookup_summary
        source_node_id = lookup_summary[req_id].get("source_node_id")
        if source_node_id is not None:
            assert source_node_id == LOOKUP_SOURCES[req_id]

    classes = {item["requirement_class"] for item in summary["system_resolved_requirements"]}
    assert "table_lookup" in classes
    assert "equation_result" in classes
    assert "report_output" in classes


def test_fresh_plan_includes_active_system_requirements() -> None:
    from engine.state.state_manager import TaskStateManager
    from models.task import TaskStatus

    manager = TaskStateManager()
    task = manager.create_task("system-reqs-fresh", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    plan = finalize_engineering_plan(build_engineering_plan(task, _reader()))

    for req_id in (*_LOOKUP_IDS, _REPORT_ID):
        assert req_id in plan.requirements
        assert plan.requirements[req_id].activation_status == "active"

    for req_id in _EQUATION_IDS:
        if req_id in plan.requirements:
            assert plan.requirements[req_id].activation_status == "active"
