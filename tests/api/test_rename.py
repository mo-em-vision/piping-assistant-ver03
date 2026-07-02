"""Tests for project and task rename API."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import ApiError, DesktopApiService
from api.serializers import _task_display_name
from cli.session_store import _task_from_dict, _task_to_dict
from config.loader import CLIConfig
from models.task import Task, TaskStatus, new_task


@pytest.fixture
def temp_service(tmp_path: Path) -> DesktopApiService:
    sessions_dir = tmp_path / "sessions"
    standards_root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    config = CLIConfig(
        report_format="pdf",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=sessions_dir,
        standards_root=standards_root,
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def test_rename_project_updates_name_and_preserves_id(temp_service: DesktopApiService) -> None:
    created = temp_service.create_project("Original Name")
    project_id = created["id"]

    renamed = temp_service.rename_project(project_id, "Renamed Project")
    assert renamed["id"] == project_id
    assert renamed["name"] == "Renamed Project"

    listed = temp_service.list_projects()
    match = next(project for project in listed if project["id"] == project_id)
    assert match["name"] == "Renamed Project"


def test_rename_project_empty_name_returns_bad_request(temp_service: DesktopApiService) -> None:
    created = temp_service.create_project("Original Name")
    with pytest.raises(ApiError) as exc_info:
        temp_service.rename_project(created["id"], "   ")

    assert exc_info.value.status == 400
    assert exc_info.value.code == "invalid_request"


def test_rename_missing_project_returns_not_found(temp_service: DesktopApiService) -> None:
    with pytest.raises(ApiError) as exc_info:
        temp_service.rename_project("missing-project-id", "New Name")

    assert exc_info.value.status == 404
    assert exc_info.value.code == "project_not_found"


def test_rename_task_updates_display_name_and_preserves_id(temp_service: DesktopApiService) -> None:
    project = temp_service.create_project("Rename Task Project")
    created = temp_service.create_task("pipe_wall_thickness_design", project["id"])
    task_id = created["task_id"]
    assert created["name"] == "Pipe Thickness Calculation"

    renamed = temp_service.rename_task(task_id, "Line 200 Thickness", project["id"])
    assert renamed["task_id"] == task_id
    assert renamed["name"] == "Line 200 Thickness"

    tasks = temp_service.list_tasks(project["id"])
    match = next(task for task in tasks["tasks"] if task["id"] == task_id)
    assert match["name"] == "Line 200 Thickness"


def test_rename_task_empty_name_returns_bad_request(temp_service: DesktopApiService) -> None:
    project = temp_service.create_project("Rename Task Project")
    created = temp_service.create_task("pipe_wall_thickness_design", project["id"])
    with pytest.raises(ApiError) as exc_info:
        temp_service.rename_task(created["task_id"], "", project["id"])

    assert exc_info.value.status == 400
    assert exc_info.value.code == "invalid_request"


def test_rename_missing_task_returns_not_found(temp_service: DesktopApiService) -> None:
    project = temp_service.create_project("Rename Task Project")
    with pytest.raises(ApiError) as exc_info:
        temp_service.rename_task("missing-task-id", "New Name", project["id"])

    assert exc_info.value.status == 404
    assert exc_info.value.code == "task_not_found"


def test_task_display_name_prefers_custom_display_name() -> None:
    task = new_task(
        "pipe-wall-thickness-desi-test01",
        status=TaskStatus.AWAITING_INPUT,
        workflow_id="pipe_wall_thickness_design",
    )
    task.outputs["display_name"] = "Custom Title"
    assert _task_display_name(task) == "Custom Title"

    round_trip = _task_from_dict(_task_to_dict(task))
    assert _task_display_name(round_trip) == "Custom Title"
