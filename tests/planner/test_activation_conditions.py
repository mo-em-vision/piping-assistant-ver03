"""Requirement activation status resolution."""

from __future__ import annotations

from engine.planner.activation_conditions import resolve_activation_status
from engine.planner.pipe_wall_plan import INTERNAL_PRESSURE_BRANCH_CONDITION, build_pipe_wall_requirements
from tests.helpers.goals import PIPE_WALL_ROOT_GOAL_ID
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import (
    external_pressure_assumption,
    internal_pressure_assumption,
    straight_section_assumption,
)


def test_resolve_activation_status_conditional_before_branch() -> None:
    requirements = build_pipe_wall_requirements(root_goal_id=PIPE_WALL_ROOT_GOAL_ID)
    req = requirements["REQ-internal_design_gage_pressure"]
    assert req.activation_condition == INTERNAL_PRESSURE_BRANCH_CONDITION
    assert resolve_activation_status(req, {}) == "conditional"


def test_resolve_activation_status_active_for_internal_pressure() -> None:
    manager = TaskStateManager()
    task = manager.create_task("activation-internal", status=TaskStatus.AWAITING_INPUT)
    facts = {
        fact.key: fact
        for fact in (
            fact_from_engineering_input(
                straight_section_assumption(),
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
            fact_from_engineering_input(
                internal_pressure_assumption(),
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    }
    requirements = build_pipe_wall_requirements(root_goal_id=PIPE_WALL_ROOT_GOAL_ID)
    req = requirements["REQ-material_grade"]
    assert resolve_activation_status(req, facts) == "active"


def test_resolve_activation_status_not_applicable_for_external_pressure() -> None:
    manager = TaskStateManager()
    task = manager.create_task("activation-external", status=TaskStatus.AWAITING_INPUT)
    facts = {
        fact.key: fact
        for fact in (
            fact_from_engineering_input(
                straight_section_assumption(),
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
            fact_from_engineering_input(
                external_pressure_assumption(),
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    }
    requirements = build_pipe_wall_requirements(root_goal_id=PIPE_WALL_ROOT_GOAL_ID)
    req = requirements["REQ-allowable_stress_lookup"]
    assert resolve_activation_status(req, facts) == "not_applicable"
