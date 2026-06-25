"""Tests for task deletion API."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import ApiError, DesktopApiService
from config.loader import CLIConfig
from engine.state.state_manager import TaskNotFoundError
from tests.api.conftest import api_session_id


@pytest.fixture
def api_service(tmp_path: Path, project_root: Path) -> DesktopApiService:
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
    return DesktopApiService(config=config, session_id="default")


def test_delete_task_removes_task_and_clears_active(api_service: DesktopApiService) -> None:
    session_id = api_session_id(api_service)
    created = api_service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    result = api_service.delete_task(task_id, session_id)
    assert result["deleted"] is True
    assert result["task_id"] == task_id

    tasks = api_service.list_tasks(session_id)
    assert tasks["active_task_id"] is None
    assert all(task["id"] != task_id for task in tasks["tasks"])

    manager = api_service._store_for(session_id).load_state_manager()
    with pytest.raises(TaskNotFoundError):
        manager.get_task(task_id)


def test_delete_missing_task_returns_not_found(api_service: DesktopApiService) -> None:
    session_id = api_session_id(api_service)
    with pytest.raises(ApiError) as exc_info:
        api_service.delete_task("missing-task-id", session_id)

    assert exc_info.value.status == 404
    assert exc_info.value.code == "task_not_found"
