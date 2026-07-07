"""Tests for engineering plan validation invariants."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.plan_validation import validate_engineering_plan
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import PlanDependency
from models.task import TaskStatus


def _fresh_plan():
    state = TaskStateManager()
    task = state.create_task("plan-validation", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    return build_pipe_wall_engineering_plan(task)


def test_validate_rejects_diameter_resolution_as_lookup_input_source() -> None:
    plan = _fresh_plan()
    plan.dependencies.append(
        PlanDependency(
            from_id="REQ-diameter_resolution",
            to_id="REQ-outside_diameter_lookup",
            type="lookup_input",
        )
    )
    result = validate_engineering_plan(plan)
    assert not result.valid
    assert any("REQ-diameter_resolution" in error for error in result.errors)


def test_validate_accepts_nominal_pipe_size_lookup_input_edge() -> None:
    plan = _fresh_plan()
    result = validate_engineering_plan(plan)
    assert result.valid, result.errors
    assert any(
        edge.from_id == "REQ-nominal_pipe_size"
        and edge.to_id == "REQ-outside_diameter_lookup"
        and edge.type == "lookup_input"
        for edge in plan.dependencies
    )
