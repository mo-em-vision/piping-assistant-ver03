"""Planner layer tests."""

from __future__ import annotations

from pathlib import Path

from engine.planner.planner import Planner
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, IntentResult
from models.task import Task, TaskStatus


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "standards", standard="asme_b31.3")


def test_planner_pipe_wall_thickness_missing_inputs() -> None:
    state = TaskStateManager()
    task = state.create_task("pipe-wall-thickness-plan", status=TaskStatus.AWAITING_INPUT)
    planner = Planner(_reader(), state=state)

    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    plan = planner.plan(intent, task)

    assert plan.selected_root == "pipe_wall_thickness_design"
    assert "B313-material-stress" in plan.selected_nodes
    assert "B313-304.1.1" in plan.selected_nodes
    assert "design_pressure" in plan.missing_inputs
    assert "material" in plan.missing_inputs
    assert plan.action == AgentAction.REQUEST_INPUT
    assert task.outputs.get("planning_summary") is not None


def test_planner_does_not_execute_calculations() -> None:
    state = TaskStateManager()
    task = state.create_task("pipe-wall-thickness-no-exec", status=TaskStatus.AWAITING_INPUT)
    planner = Planner(_reader(), state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    planner.plan(intent, task)

    assert "required_thickness" not in task.outputs
    assert "_execution_trace" not in task.outputs


def test_planner_ambiguous_integrity_request() -> None:
    state = TaskStateManager()
    task = Task(task_id="ambiguous", status=TaskStatus.ACTIVE)
    planner = Planner(_reader(), state=state)
    intent = IntentResult(
        intent=None,
        domain="piping",
        confidence=0.3,
    )

    plan = planner.plan(intent, task, user_message="verify pipe integrity")

    assert plan.action == AgentAction.CLARIFY
    assert plan.alternative_paths
