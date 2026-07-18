"""Tests for planner inspector view projections (header, phase panel, traversal path)."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.plan_inspector import build_planner_inspector_summary
from engine.planner.plan_validation import validate_engineering_plan
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import (
    internal_pressure_assumption,
    straight_section_assumption,
)


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _fresh_task():
    manager = TaskStateManager()
    task = manager.create_task("inspector-views-fresh", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def _task_after_straight_pipe(manager: TaskStateManager, task):
    manager.store_fact(
        task.task_id,
        fact_from_engineering_input(
            straight_section_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    return manager.get_task(task.task_id)


def _task_after_pressure(manager: TaskStateManager, task):
    task = _task_after_straight_pipe(manager, task)
    manager.store_fact(
        task.task_id,
        fact_from_engineering_input(
            internal_pressure_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    return manager.get_task(task.task_id)


@pytest.mark.parametrize(
    ("build_task", "expected_badge", "expected_active_field"),
    [
        ("fresh", "waiting_for_input", "straight_pipe_section"),
        ("after_straight", "waiting_for_input", "pressure_design_case"),
        ("after_pressure", "waiting_for_input", None),
    ],
)
def test_planner_header_and_phase_panel_stages(
    build_task: str,
    expected_badge: str,
    expected_active_field: str | None,
) -> None:
    manager, task = _fresh_task()
    if build_task == "after_straight":
        task = _task_after_straight_pipe(manager, task)
    elif build_task == "after_pressure":
        task = _task_after_pressure(manager, task)

    plan = build_engineering_plan(task, _reader())
    assert validate_engineering_plan(plan).valid
    summary = build_planner_inspector_summary(plan)

    assert "header" in summary
    assert summary["header"]["status_badge"] == expected_badge
    assert summary["header"]["workflow_id"] == "pipe_wall_thickness_design"
    assert summary["header"]["why_here"]

    assert "phase_panel" in summary
    phase_panel = summary["phase_panel"]
    if expected_active_field:
        assert phase_panel["active_field"] == expected_active_field

    current_fields = {item["field"] for item in summary["current_phase_inputs"]}
    future_fields = {item["field"] for item in summary["future_phase_inputs"]}
    assert current_fields.isdisjoint(future_fields)


def test_fresh_pipe_wall_traversal_path_and_requirements_panel() -> None:
    _, task = _fresh_task()
    plan = build_engineering_plan(task, _reader())
    summary = build_planner_inspector_summary(plan)

    assert summary["traversal_path"]
    states = {row["state"] for row in summary["traversal_path"]}
    assert "current" in states or "pending" in states

    lookup_rows = [
        row for row in summary["requirements_panel"] if row["category"] == "lookup_derived"
    ]
    assert lookup_rows
    assert all(row["awaiting_user_input"] is False for row in lookup_rows)


def test_planner_header_traversal_support_pipe_wall() -> None:
    _, task = _fresh_task()
    plan = build_engineering_plan(task, _reader())
    summary = build_planner_inspector_summary(plan)
    assert summary["header"]["traversal_support_level"] == "full"


def test_planner_header_traversal_support_non_pipe_wall() -> None:
    plan = _synthetic_generic_plan_with_traversal()
    summary = build_planner_inspector_summary(plan)
    assert summary["header"]["traversal_support_level"] == "full"
    assert summary["header"]["traversal_support_note"] is None


def _synthetic_generic_plan_with_traversal():
    from models.engineering_plan import (
        CalculationGoal,
        EngineeringPlan,
        PlanGraph,
        PlannerTraversalState,
        TraversalExpandedNode,
        new_plan_id,
    )

    return EngineeringPlan(
        plan_id=new_plan_id(),
        task_id="task-generic",
        workflow_id="generic_sample_workflow",
        root_goal=CalculationGoal(
            id="GOAL-generic",
            key="calculate-generic",
            title="Generic Workflow",
            target_field="generic_output",
        ),
        graph=PlanGraph(),
        phases=[],
        traversal=PlannerTraversalState(
            traversal_id="TRAV-generic",
            expanded_nodes=[
                TraversalExpandedNode(
                    node_id="WF-GENERIC",
                    node_type="workflow",
                    expanded_at_order=1,
                    title="Generic Workflow",
                )
            ],
        ),
    )


def test_requirements_panel_resolution_labels() -> None:
    _, task = _fresh_task()
    plan = build_engineering_plan(task, _reader())
    summary = build_planner_inspector_summary(plan)
    lookup_rows = [row for row in summary["requirements_panel"] if row["category"] == "lookup_derived"]
    assert lookup_rows
    assert all(row["resolution_label"] == "Lookup-derived" for row in lookup_rows)
    assert all(row["awaiting_user_input"] is False for row in lookup_rows)


def test_planner_inspector_summary_rebuild_includes_new_fields() -> None:
    _, task = _fresh_task()
    plan = build_engineering_plan(task, _reader())
    summary = build_planner_inspector_summary(plan)

    for key in (
        "header",
        "phase_panel",
        "traversal_path",
        "requirements_panel",
        "current_phase_inputs",
        "future_phase_inputs",
    ):
        assert key in summary
