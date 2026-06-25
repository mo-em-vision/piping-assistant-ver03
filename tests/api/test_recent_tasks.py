"""Tests for cross-project recent tasks API."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from api.desktop_service import ApiError, DesktopApiService
from config.loader import CLIConfig
from models.task import TaskStatus
from storage.project_session_store import ProjectSessionStore


@pytest.fixture
def temp_service(tmp_path: Path) -> DesktopApiService:
    sessions_dir = tmp_path / "sessions"
    standards_root = Path(__file__).resolve().parents[2] / "standards"
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


def test_list_projects_empty_on_fresh_db(temp_service: DesktopApiService) -> None:
    assert temp_service.list_projects() == []


def test_list_tasks_requires_session_id(temp_service: DesktopApiService) -> None:
    with pytest.raises(ApiError) as exc_info:
        temp_service.list_tasks(None)
    assert exc_info.value.code == "project_required"


def test_recent_tasks_across_projects_ordered_by_updated_at(temp_service: DesktopApiService) -> None:
    project_a = temp_service.create_project("Project A")
    project_b = temp_service.create_project("Project B")

    task_a = temp_service.create_task("pipe_wall_thickness_design", project_a["id"])
    time.sleep(0.01)
    task_b = temp_service.create_task("pipe_wall_thickness_design", project_b["id"])

    recent = temp_service.list_recent_tasks_global()["recent_tasks"]

    assert len(recent) == 2
    assert recent[0]["id"] == task_b["task_id"]
    assert recent[0]["project_id"] == project_b["id"]
    assert recent[0]["project_name"] == "Project B"
    assert recent[1]["id"] == task_a["task_id"]
    assert recent[1]["project_id"] == project_a["id"]


def test_recent_tasks_excludes_completed(temp_service: DesktopApiService) -> None:
    project = temp_service.create_project("Completed Filter")
    session_id = project["id"]

    created = temp_service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    database = temp_service._database()
    store = ProjectSessionStore(database, temp_service.config.sessions_dir, session_id=session_id)
    manager = store.load_state_manager()
    task = manager.get_task(task_id)
    task.status = TaskStatus.COMPLETED
    manager.replace_task(task_id, task)
    store.save_state_manager(manager)

    recent = temp_service.list_recent_tasks_global()["recent_tasks"]
    assert all(item["id"] != task_id for item in recent)
