"""Requirement activation status resolution."""

from __future__ import annotations

from engine.planner.activation_conditions import resolve_activation_status
from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import (
    external_pressure_assumption,
    internal_pressure_assumption,
    straight_section_assumption,
)
from tests.planner.helpers import _reader


def _pipe_wall_requirements():
    state = TaskStateManager()
    task = state.create_task("activation-reqs", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    plan = build_engineering_plan(task, _reader())
    assert plan is not None
    return plan.requirements


def test_resolve_activation_status_conditional_before_branch() -> None:
    requirements = _pipe_wall_requirements()
    req = requirements["REQ-internal_design_gage_pressure"]
    assert req.activation_condition is not None
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
    requirements = _pipe_wall_requirements()
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
    requirements = _pipe_wall_requirements()
    req = requirements["REQ-allowable_stress_lookup"]
    assert resolve_activation_status(req, facts) == "not_applicable"
