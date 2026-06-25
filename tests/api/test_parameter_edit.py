"""Tests for timeline parameter edit flow."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from api.parameter_definitions import build_parameter_definitions, submit_task_input
from api.parameter_edit import assess_parameter_edit, begin_parameter_edit
from api.workflow_timeline import submittable_parameter_ids


def _sample_task(manager: TaskStateManager) -> str:
    task = manager.create_task("pipe-wall-thickness-desi-edit01", status=TaskStatus.COMPLETED)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "required_thickness": 4.2,
        "planning_summary": {"current_phase": "ready", "phase_missing": {}},
    }
    for input_id, value in (
        ("pressure_loading", "internal_pressure"),
        ("material", "SA-106B"),
        ("design_pressure", 8.0),
        ("design_temperature", 38.0),
        ("nominal_pipe_size", "6"),
    ):
        task.inputs[input_id] = EngineeringInput(
            input_id=input_id,
            value=value,
            unit="dimensionless" if input_id in {"material", "nominal_pipe_size", "pressure_loading"} else ("bar" if input_id == "design_pressure" else "C"),
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        )
    manager.replace_task(task.task_id, task)
    return task.task_id


def test_assess_parameter_edit_flags_pressure_loading_path_change() -> None:
    manager = TaskStateManager()
    task_id = _sample_task(manager)
    task = manager.get_task(task_id)

    impact = assess_parameter_edit(task, "pressure_loading")

    assert impact["affects_path"] is True
    assert impact["affects_design"] is True
    assert "design_pressure" in impact["downstream_parameters"]


def test_begin_parameter_edit_clears_downstream_and_opens_edit_session() -> None:
    manager = TaskStateManager()
    task_id = _sample_task(manager)
    task = manager.get_task(task_id)

    begin_parameter_edit(task, "design_pressure")
    manager.replace_task(task_id, task)

    assert task.status == TaskStatus.AWAITING_INPUT
    assert "design_temperature" not in task.inputs
    assert task.outputs.get("required_thickness") is None
    assert task.outputs["edit_session"]["parameter"] == "design_pressure"

    planning = task.outputs["planning_summary"]
    assert submittable_parameter_ids(task, planning) == ["design_pressure"]

    parameters = build_parameter_definitions(task)
    edited = next(item for item in parameters if item["name"] == "design_pressure")
    assert edited["status"] == "pending"
    assert edited["editing"] is True


def test_submit_after_edit_clears_edit_session() -> None:
    manager = TaskStateManager()
    task_id = _sample_task(manager)
    task = manager.get_task(task_id)
    begin_parameter_edit(task, "design_pressure")
    manager.replace_task(task_id, task)

    submit_task_input(
        manager,
        task_id,
        parameter="design_pressure",
        value=10.0,
        unit="bar",
    )

    updated = manager.get_task(task_id)
    assert "edit_session" not in updated.outputs
    assert updated.inputs["design_pressure"].value == 10.0


def test_desktop_service_preview_parameter_edit(tmp_path, project_root) -> None:
    from config.loader import CLIConfig

    from api.desktop_service import DesktopApiService
    from tests.api.conftest import api_session_id

    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    service = DesktopApiService(config=config, session_id="default")
    session_id = api_session_id(service)
    manager = TaskStateManager()
    task_id = _sample_task(manager)
    service._save_manager(manager, session_id)

    impact = service.preview_parameter_edit(task_id, "design_pressure", session_id)

    assert impact["parameter"] == "design_pressure"
    assert impact["affects_design"] is True
