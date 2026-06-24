"""Tests for desktop REST API serializers."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task, TaskStatus

from api.serializers import task_state, task_summary, workflow_catalog


def test_workflow_catalog_includes_pipe_wall_thickness() -> None:
    workflows = workflow_catalog()
    ids = {item["id"] for item in workflows}
    assert "pipe_wall_thickness_design" in ids


def test_task_summary_uses_workflow_metadata() -> None:
    task = Task(
        task_id="pipe-wall-thickness-desi-test01",
        status=TaskStatus.AWAITING_INPUT,
        outputs={"workflow": "pipe_wall_thickness_design"},
    )
    summary = task_summary(task)
    assert summary["name"] == "Pipe Thickness Calculation"
    assert summary["workflow_id"] == "pipe_wall_thickness_design"


def test_task_state_includes_curated_timeline() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test02", status=TaskStatus.AWAITING_INPUT)
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
    task.inputs["straight_pipe_section"] = EngineeringInput(
        input_id="straight_pipe_section",
        value=True,
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    task.inputs["pressure_loading"] = EngineeringInput(
        input_id="pressure_loading",
        value="internal_pressure",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "missing_inputs": ["nominal_pipe_size"],
            "missing_assumptions": [],
            "current_phase": "parameter_gathering",
            "phase_missing": {"parameter_gathering": ["nominal_pipe_size"]},
        },
    }
    manager.replace_task(task.task_id, task)

    state = task_state(task, manager)
    titles = [step["title"] for step in state["progress"]["timeline"]]
    assert titles == [
        "Pressure loading",
        "Material",
        "Design pressure",
        "Nominal pipe size",
        "Thickness",
        "Report",
    ]
    assert state["progress"]["timeline"][0]["display_value"] == "The pipe is internally pressurized."
    assert state["progress"]["timeline"][1]["display_value"] == "SA-106B"
    assert state["progress"]["timeline"][2]["display_value"] == "8.0 bar"
    assert state["progress"]["timeline"][3]["status"] == "active"
    report_step = next(step for step in state["progress"]["timeline"] if step["id"] == "report")
    assert report_step["status"] == "pending"
    assert state["progress"]["completed_count"] == 3
    assert any(item["name"] == "nominal_pipe_size" for item in state["parameters"])
    assert any(item["name"] == "material" for item in state["parameters"])
    assert isinstance(state["display_outputs"], list)


def test_task_state_timeline_includes_coefficient_parameters() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test06", status=TaskStatus.AWAITING_INPUT)
    task.inputs["pressure_loading"] = EngineeringInput(
        input_id="pressure_loading",
        value="internal_pressure",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
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
    task.inputs["design_temperature"] = EngineeringInput(
        input_id="design_temperature",
        value=200.0,
        unit="C",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    task.inputs["nominal_pipe_size"] = EngineeringInput(
        input_id="nominal_pipe_size",
        value="10",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "allowable_stress": 193.0,
        "planning_summary": {
            "missing_inputs": [],
            "missing_assumptions": [],
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

    state = task_state(task, manager)
    titles = [step["title"] for step in state["progress"]["timeline"]]
    assert "Joint efficiency (E)" in titles
    assert "Weld strength reduction (W)" in titles
    assert "Temperature coefficient (Y)" in titles
    assert "Allowable stress (S)" in titles
    assert state["progress"]["timeline"][titles.index("Allowable stress (S)")]["status"] == "done"
    assert state["progress"]["timeline"][titles.index("Joint category")]["status"] == "active"
    param_names = [item["name"] for item in state["parameters"]]
    assert "weld_joint_efficiency" in param_names
    assert "material" in param_names


def test_task_state_report_step_active_after_thickness_complete() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test07", status=TaskStatus.AWAITING_INPUT)
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
        "required_thickness": 12.5,
        "thickness_unit": "mm",
        "planning_summary": {
            "missing_inputs": [],
            "missing_assumptions": [],
            "current_phase": "ready",
        },
    }
    manager.replace_task(task.task_id, task)

    state = task_state(task, manager)
    timeline = state["progress"]["timeline"]
    thickness_step = next(step for step in timeline if step["id"] == "thickness")
    report_step = next(step for step in timeline if step["id"] == "report")

    assert thickness_step["status"] == "done"
    assert report_step["status"] == "active"
    assert report_step["hint"] == "Generate the engineering report"


def test_task_state_includes_calculation_error_when_invalidated() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test03", status=TaskStatus.INVALIDATED)
    task.warnings = ["Wall thickness below minimum allowable."]
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    manager.replace_task(task.task_id, task)

    state = task_state(task, manager)
    assert len(state["errors"]) == 1
    assert state["errors"][0]["code"] == "calculation_failed"
    assert state["errors"][0]["recovery"]["title"] == "Calculation failed"
    assert "Wall thickness" in state["errors"][0]["message"]
