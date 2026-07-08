"""Tests for read-only planner_debug_projection dev inspection view."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.plan_inspector import build_planner_inspector_summary
from engine.planner.planner_debug_projection import build_planner_debug_projection
from engine.planner.plan_validation import validate_engineering_plan
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import (
    CalculationGoal,
    EngineeringPlan,
    InputStrategy,
    PlanGraph,
    PlanRequirement,
    PlannerTraversalState,
    QuestionSpec,
    TraversalActiveNode,
    TraversalExpandedNode,
    TraversalPendingNode,
    new_plan_id,
)
from models.task import TaskStatus


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("debug-projection-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def _synthetic_generic_plan() -> EngineeringPlan:
    """Non-pipe-wall workflow snapshot with traversal data for generic projection tests."""
    req = PlanRequirement(
        id="REQ-sample_input",
        field="sample_input",
        parameter_node_id="PARAM-sample-input",
        requirement_class="user_input",
        status="missing",
        phase="parameter_gathering",
        key="input-sample_input",
        title="Sample Input",
        question_spec=QuestionSpec(
            field="sample_input",
            label="Sample Input",
            expected_value_class="selection",
            priority=10,
            ask_policy="ask_now",
            reason_code="required_for_generic_workflow",
        ),
    )
    traversal = PlannerTraversalState(
        traversal_id="TRAV-synthetic",
        current_active_node_id="NODE-sample",
        current_active_node=TraversalActiveNode(
            node_id="NODE-sample",
            node_type="parameter",
            title="Sample Input",
            phase="parameter_gathering",
            reason="Active parameter on generic workflow path",
        ),
        expanded_nodes=[
            TraversalExpandedNode(
                node_id="WF-GENERIC",
                node_type="workflow",
                expanded_at_order=1,
                title="Generic Workflow",
            )
        ],
        pending_expansion_nodes=[
            TraversalPendingNode(
                node_id="NODE-pending",
                node_type="paragraph",
                waiting_on=["NODE-sample"],
                reason="Blocked until sample input is provided",
                title="Pending Paragraph",
            )
        ],
    )
    return EngineeringPlan(
        plan_id=new_plan_id(),
        task_id="task-synthetic",
        workflow_id="generic_sample_workflow",
        root_goal=CalculationGoal(
            id="GOAL-sample",
            key="calculate-sample",
            title="Generic Sample Calculation",
            target_field="sample_output",
            status="blocked",
        ),
        requirements={"REQ-sample_input": req},
        input_strategy=InputStrategy(
            mode="sequential",
            current_phase="parameter_gathering",
            resolved_fields=[],
            blocked_fields=[],
            next_fields=["sample_input"],
        ),
        graph=PlanGraph(),
        phases=[],
        traversal=traversal,
        debug={"validation_warnings": [], "validation_errors": []},
    )


def test_projection_top_level_keys_present() -> None:
    plan = _synthetic_generic_plan()
    projection = build_planner_debug_projection(plan)

    for key in (
        "workflow_title",
        "workflow_slug",
        "planner_confidence",
        "planner_reason",
        "current_step",
        "active_node",
        "visited_timeline",
        "pending_nodes",
        "pending_calculations",
        "pending_validations",
        "pending_lookups",
        "required_inputs",
        "blocked_reason",
        "next_expected_action",
        "warnings",
        "raw_planner_state",
    ):
        assert key in projection


def test_projection_does_not_invent_confidence_or_reason() -> None:
    plan = _synthetic_generic_plan()
    projection = build_planner_debug_projection(plan)
    assert projection["planner_confidence"] is None
    assert projection["planner_reason"] is None


def test_synthetic_non_pipe_wall_traversal_timeline() -> None:
    plan = _synthetic_generic_plan()
    projection = build_planner_debug_projection(plan)

    assert projection["workflow_slug"] == "generic_sample_workflow"
    assert projection["workflow_title"] == "Generic Sample Calculation"
    assert projection["visited_timeline"]
    statuses = {row["status"] for row in projection["visited_timeline"]}
    assert "visited" in statuses
    assert "active" in statuses
    assert projection["pending_nodes"]
    assert projection["pending_nodes"][0]["node_id"] == "NODE-pending"


def test_blocked_reason_waiting_for_user_input() -> None:
    plan = _synthetic_generic_plan()
    projection = build_planner_debug_projection(plan)
    blocked = projection["blocked_reason"]
    assert blocked["kind"] == "waiting_for_user_input"
    assert blocked["missing_item"] == "sample_input"
    assert projection["required_inputs"]
    assert projection["required_inputs"][0]["key"] == "sample_input"


def test_blocked_reason_not_available_when_unclassifiable() -> None:
    plan = _synthetic_generic_plan()
    plan.requirements.clear()
    plan.input_strategy = None
    plan.traversal = None
    projection = build_planner_debug_projection(plan)
    assert projection["blocked_reason"]["kind"] == "not_available"


def test_required_inputs_have_no_nested_json_blobs() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    projection = build_planner_debug_projection(plan)
    for row in projection["required_inputs"]:
        for value in row.values():
            assert not isinstance(value, (dict, list))


def test_raw_planner_state_only_in_advanced_payload() -> None:
    plan = _synthetic_generic_plan()
    projection = build_planner_debug_projection(plan)
    raw = projection["raw_planner_state"]
    assert "engineering_plan" in raw
    assert "planner_inspector_summary" in raw
    assert projection["workflow_slug"] == plan.workflow_id
    assert "requirements" not in projection


def test_pipe_wall_integration_projection() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    assert validate_engineering_plan(plan).valid
    projection = build_planner_debug_projection(plan, reader=_reader())

    assert projection["workflow_slug"] == "pipe_wall_thickness_design"
    assert projection["blocked_reason"]["kind"] == "waiting_for_user_input"
    assert projection["visited_timeline"]
    assert projection["required_inputs"]


def test_planner_inspector_summary_traversal_support_non_pipe_wall_with_traversal() -> None:
    plan = _synthetic_generic_plan()
    summary = build_planner_inspector_summary(plan)
    assert summary["header"]["traversal_support_level"] == "full"
    assert summary["header"]["traversal_support_note"] is None


def test_planner_debug_projection_for_task_from_outputs() -> None:
    from engine.planner.planner_debug_projection import planner_debug_projection_for_task

    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    task.outputs["engineering_plan"] = plan.to_dict()

    projection = planner_debug_projection_for_task(task, reader=_reader())
    assert projection is not None
    assert projection["workflow_slug"] == "pipe_wall_thickness_design"
