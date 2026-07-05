"""Tests for goal-guided workflow navigation."""

from __future__ import annotations

from engine.planner.goal_navigation import (
    build_current_ask,
    goal_guided_parameter_ids,
    next_actionable_goal,
)
from engine.state.goal_projection import planning_projection
from models.goal import goal_parameter_key
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.helpers.goals import task_with_planning


def _pipe_wall_task_with_pressure_loading_goal() -> tuple:
    manager = TaskStateManager()
    task = manager.create_task("goal-nav-test01", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_assumptions": ["pressure_loading"],
        "current_phase": "path_decisions",
        "phase_missing": {"path_decisions": ["pressure_loading"]},
        "phase_questions": {
            "path_decisions": {
                "pressure_loading": "Is the pipe subjected to internal or external pressure?",
            }
        },
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)
    return manager, manager.get_task(task.task_id)


def test_next_actionable_goal_returns_pressure_loading_first() -> None:
    _, task = _pipe_wall_task_with_pressure_loading_goal()
    goal = next_actionable_goal(task)
    assert goal is not None
    assert goal_parameter_key(goal) == "pressure_loading"
    assert goal_guided_parameter_ids(task) == ["pressure_loading"]


def test_build_current_ask_for_expansion_gate() -> None:
    _, task = _pipe_wall_task_with_pressure_loading_goal()
    planning = planning_projection(task)
    ask = build_current_ask(task, planning)
    assert ask is not None
    assert ask["kind"] == "input"
    assert ask["parameter_id"] == "pressure_loading"
    assert "internal or external pressure" in str(ask["prompt"])


def test_build_current_ask_falls_back_to_submittable_parameter() -> None:
    manager = TaskStateManager()
    task = manager.create_task("goal-nav-fallback", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "current_phase": "path_decisions",
        "phase_missing": {"path_decisions": ["pressure_loading"]},
        "phase_questions": {
            "path_decisions": {
                "pressure_loading": "Is the pipe subjected to internal or external pressure?",
            }
        },
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "phase_allowed_fields": {"path_decisions": ["pressure_loading"]},
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    for goal in list(task.goal_store.goals.values()):
        if goal.key != "verify-engineering-goal":
            task.goal_store.goals.pop(goal.id, None)

    ask = build_current_ask(task, planning)
    assert ask is not None
    assert ask["kind"] == "input"
    assert ask["parameter_id"] == "pressure_loading"


def test_next_actionable_goal_advances_after_pressure_loading() -> None:
    manager = TaskStateManager()
    task = manager.create_task("goal-nav-test02", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "current_phase": "parameter_gathering",
        "phase_missing": {
            "path_decisions": [],
            "parameter_gathering": ["design_pressure", "material"],
        },
        "phase_questions": {
            "parameter_gathering": {
                "design_pressure": "Enter the design pressure.",
                "material": "Select the pipe material.",
            }
        },
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design", "graph_input_order": ["design_pressure", "material"]}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)

    goal = next_actionable_goal(task)
    assert goal is not None
    assert goal_parameter_key(goal) == "design_pressure"
