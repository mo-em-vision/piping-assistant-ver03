"""Tests for parameter definitions and input submission."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus

from api.parameter_definitions import build_parameter_definitions, submit_task_input


def test_build_parameter_definitions_from_missing_inputs() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test03", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "missing_inputs": ["design_pressure", "material"],
            "missing_assumptions": ["pressure_loading"],
        },
    }
    manager.replace_task(task.task_id, task)

    parameters = build_parameter_definitions(manager.get_task(task.task_id))
    names = [item["name"] for item in parameters]
    assert names == ["design_pressure", "material", "pressure_loading"]

    pressure = next(item for item in parameters if item["name"] == "design_pressure")
    assert pressure["type"] == "number"
    assert "bar" in pressure["units"]
    assert pressure["status"] == "pending"


def test_submit_task_input_stores_confirmed_value() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test04", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "missing_inputs": ["design_pressure"],
            "missing_assumptions": [],
        },
    }
    manager.replace_task(task.task_id, task)

    updated = submit_task_input(
        manager,
        task.task_id,
        parameter="design_pressure",
        value=10.0,
        unit="bar",
    )

    stored = updated.inputs["design_pressure"]
    assert stored.value == 10.0
    assert stored.unit == "bar"
    planning = updated.outputs["planning_summary"]
    assert "design_pressure" not in planning["missing_inputs"]


def test_submit_task_input_rejects_unknown_parameter() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test05", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {"missing_inputs": [], "missing_assumptions": []},
    }
    manager.replace_task(task.task_id, task)

    try:
        submit_task_input(
            manager,
            task.task_id,
            parameter="unknown_parameter",
            value=1,
            unit=None,
        )
    except ValueError as exc:
        assert "not currently requested" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown parameter")
