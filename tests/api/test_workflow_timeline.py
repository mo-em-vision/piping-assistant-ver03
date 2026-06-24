"""Tests for dynamic pipe-wall workflow timeline helpers."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from api.workflow_timeline import revealed_pipe_wall_input_ids, submittable_parameter_ids


def test_revealed_inputs_include_current_and_completed_phases() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-timeline01", status=TaskStatus.AWAITING_INPUT)
    task.inputs["material"] = EngineeringInput(
        input_id="material",
        value="SA-106B",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    task.inputs["design_pressure"] = EngineeringInput(
        input_id="design_pressure",
        value=8.0,
        unit="bar",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "current_phase": "parameter_gathering",
            "phase_missing": {
                "parameter_gathering": ["nominal_pipe_size"],
                "coefficient_resolution": [
                    "joint_category",
                    "weld_joint_efficiency",
                    "weld_strength_reduction",
                    "temperature_coefficient",
                ],
            },
        },
    }
    manager.replace_task(task.task_id, task)

    revealed = revealed_pipe_wall_input_ids(task, task.outputs["planning_summary"])
    assert revealed == [
        "material",
        "design_pressure",
        "nominal_pipe_size",
    ]


def test_revealed_inputs_expand_into_coefficient_phase() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-timeline02", status=TaskStatus.AWAITING_INPUT)
    for input_id, value in (
        ("material", "SA-106B"),
        ("design_pressure", 8.0),
        ("design_temperature", 200.0),
        ("nominal_pipe_size", "10"),
    ):
        task.inputs[input_id] = EngineeringInput(
            input_id=input_id,
            value=value,
            unit="dimensionless" if input_id in {"material", "nominal_pipe_size"} else ("bar" if input_id == "design_pressure" else "C"),
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        )
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "allowable_stress": 193.0,
        "planning_summary": {
            "current_phase": "coefficient_resolution",
            "phase_missing": {
                "coefficient_resolution": [
                    "joint_category",
                    "weld_joint_efficiency",
                    "weld_strength_reduction",
                    "temperature_coefficient",
                ],
            },
        },
    }
    manager.replace_task(task.task_id, task)

    revealed = revealed_pipe_wall_input_ids(task, task.outputs["planning_summary"])
    assert "allowable_stress" in revealed
    assert "weld_joint_efficiency" in revealed
    assert "weld_strength_reduction" in revealed
    assert "temperature_coefficient" in revealed
    assert revealed.index("allowable_stress") < revealed.index("weld_joint_efficiency")


def test_submittable_parameters_remain_phase_scoped() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-timeline03", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "current_phase": "coefficient_resolution",
            "phase_missing": {
                "coefficient_resolution": ["weld_joint_efficiency"],
            },
        },
    }
    manager.replace_task(task.task_id, task)

    submittable = submittable_parameter_ids(task, task.outputs["planning_summary"])
    assert submittable == ["weld_joint_efficiency"]


def test_submittable_includes_unconfirmed_proposed_defaults_in_current_phase() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-timeline04", status=TaskStatus.AWAITING_INPUT)
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
            "current_phase": "coefficient_resolution",
            "phase_missing": {
                "coefficient_resolution": ["weld_joint_efficiency"],
            },
        },
    }
    manager.replace_task(task.task_id, task)

    submittable = submittable_parameter_ids(task, task.outputs["planning_summary"])
    assert submittable == ["joint_category", "weld_joint_efficiency"]
