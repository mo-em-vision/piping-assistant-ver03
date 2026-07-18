"""Pipe wall activation and internal/external pressure branching contract tests."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.planner.helpers import _reader
from tests.planner.plan_contract import (
    REQ_MINIMUM_REQUIRED_THICKNESS_EQ,
    REQ_REQUIRED_WALL_THICKNESS,
)

_INTERNAL_PRESSURE_CONDITIONAL_REQUIREMENT_IDS = (
    "REQ-internal_design_gage_pressure",
    "REQ-diameter_resolution",
    "REQ-material_grade",
    "REQ-design_temperature",
    "REQ-corrosion_allowance",
    "REQ-pipe_construction_type",
    REQ_REQUIRED_WALL_THICKNESS,
    REQ_MINIMUM_REQUIRED_THICKNESS_EQ,
)


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("activation-branch-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def _build_plan(*inputs):
    manager, task = _fresh_pipe_wall_task()
    for inp in inputs:
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    task = manager.get_task(task.task_id)
    existing = dict(task.fact_store.active_facts())
    plan = build_engineering_plan(task, _reader(), existing_inputs=existing)
    return plan


def _assert_internal_pressure_branch_condition(req) -> None:
    condition = req.activation_condition
    assert condition is not None
    assert condition.field == "pressure_design_case"
    assert condition.operator == "equals"
    assert condition.value == "internal_pressure"


def test_fresh_plan_internal_pressure_requirements_are_conditional_with_full_branch_condition() -> None:
    plan = _build_plan()

    for req_id in _INTERNAL_PRESSURE_CONDITIONAL_REQUIREMENT_IDS:
        req = plan.requirements[req_id]
        assert req.activation_status == "conditional", req_id
        _assert_internal_pressure_branch_condition(req)
