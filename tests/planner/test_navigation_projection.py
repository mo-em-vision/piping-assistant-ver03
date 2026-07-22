"""Tests for EngineeringPlan -> NavigationPlan projection."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.navigation_projection import navigation_plan_from_engineering_plan
from engine.planner.plan_selection import engineering_plan_for_task
from engine.planner.planner import Planner
from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, IntentResult
from models.task import TaskStatus
from tests.planner.helpers import _reader


def _fresh_task():
    manager = TaskStateManager()
    task = manager.create_task("nav-projection-test", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def test_planner_plan_stores_engineering_plan() -> None:
    manager, task = _fresh_task()
    planner = Planner(_reader(), state=manager)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    navigation = planner.plan(intent, task)

    stored = engineering_plan_for_task(task)
    assert stored is not None
    assert stored.workflow_id == "pipe_wall_thickness_design"
    assert navigation.selected_root == "pipe_wall_thickness_design"
    assert navigation.action == AgentAction.REQUEST_INPUT
    assert "straight_pipe_section" in navigation.missing_assumptions


def test_navigation_projection_matches_engineering_plan_phase() -> None:
    _, task = _fresh_task()
    reader = _reader()
    plan = build_engineering_plan(task, reader)
    assert plan is not None

    projected = navigation_plan_from_engineering_plan(
        plan,
        task=task,
        reader=reader,
    )

    assert projected.current_phase.value == plan.input_strategy.current_phase
    assert projected.selected_root == plan.workflow_id
    assert projected.missing_assumptions
