"""Tests for parameter definitions and input submission."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from api.parameter_definitions import build_parameter_definitions, submit_task_input


def test_build_parameter_definitions_includes_revealed_pipe_wall_inputs() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test07", status=TaskStatus.AWAITING_INPUT)
    task.inputs["material"] = EngineeringInput(
        input_id="material",
        value="SA-106B",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "missing_inputs": ["design_pressure"],
            "missing_assumptions": [],
            "current_phase": "parameter_gathering",
            "phase_missing": {"parameter_gathering": ["design_pressure"]},
        },
    }
    manager.replace_task(task.task_id, task)

    parameters = build_parameter_definitions(manager.get_task(task.task_id))
    names = [item["name"] for item in parameters]
    assert names == ["material", "design_pressure"]
    assert parameters[0]["status"] == "confirmed"
    assert parameters[1]["status"] == "pending"


def test_build_parameter_definitions_from_missing_inputs() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test03", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "missing_inputs": ["design_pressure", "material"],
            "missing_assumptions": ["pressure_loading"],
            "current_phase": "path_decisions",
            "phase_missing": {"path_decisions": ["pressure_loading"]},
        },
    }
    manager.replace_task(task.task_id, task)

    parameters = build_parameter_definitions(manager.get_task(task.task_id))
    names = [item["name"] for item in parameters]
    assert names == ["pressure_loading"]

    pressure = next(item for item in parameters if item["name"] == "pressure_loading")
    assert pressure["type"] == "dropdown"
    assert pressure["status"] == "pending"
    assert pressure["submittable"] is True


def test_build_parameter_definitions_marks_only_submittable_fields() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test08", status=TaskStatus.AWAITING_INPUT)
    task.inputs["joint_category"] = EngineeringInput(
        input_id="joint_category",
        value="seamless",
        unit="dimensionless",
        source=InputSource.DEFAULT,
        status=InputStatus.PROPOSED_DEFAULT,
        default="seamless",
        requires_confirmation=True,
    )
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "current_phase": "parameter_gathering",
            "phase_missing": {
                "parameter_gathering": ["design_pressure"],
            },
        },
    }
    manager.replace_task(task.task_id, task)

    parameters = {item["name"]: item for item in build_parameter_definitions(manager.get_task(task.task_id))}
    assert parameters["design_pressure"]["submittable"] is True
    assert parameters["joint_category"]["submittable"] is False


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
