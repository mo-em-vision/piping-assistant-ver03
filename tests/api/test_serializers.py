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
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "missing_inputs": ["nominal_pipe_size"],
            "missing_assumptions": [],
        },
    }
    manager.replace_task(task.task_id, task)

    state = task_state(task, manager)
    titles = [step["title"] for step in state["progress"]["timeline"]]
    assert titles == ["Material", "Pressure", "Thickness", "Report"]
    assert state["progress"]["timeline"][0]["display_value"] == "SA-106B"
    assert state["progress"]["timeline"][1]["display_value"] == "8.0 bar"
    assert state["progress"]["timeline"][2]["status"] == "active"
    assert state["progress"]["completed_count"] == 2
    assert any(item["name"] == "nominal_pipe_size" for item in state["parameters"])
    assert isinstance(state["display_outputs"], list)


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
