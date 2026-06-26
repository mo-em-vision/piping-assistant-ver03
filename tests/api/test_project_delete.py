"""Tests for project deletion API."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import ApiError, DesktopApiService
from config.loader import CLIConfig


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


def test_delete_empty_project(temp_service: DesktopApiService) -> None:
    created = temp_service.create_project("Empty Project")
    project_id = created["id"]

    result = temp_service.delete_project(project_id)
    assert result["deleted"] is True
    assert result["id"] == project_id
    assert all(project["id"] != project_id for project in temp_service.list_projects())


def test_delete_project_with_tasks(temp_service: DesktopApiService) -> None:
    created = temp_service.create_project("Project With Tasks")
    project_id = created["id"]
    temp_service.create_task("pipe_wall_thickness_design", project_id)

    result = temp_service.delete_project(project_id)
    assert result["deleted"] is True
    assert all(project["id"] != project_id for project in temp_service.list_projects())


def test_delete_missing_project_returns_not_found(temp_service: DesktopApiService) -> None:
    with pytest.raises(ApiError) as exc_info:
        temp_service.delete_project("missing-project-id")

    assert exc_info.value.status == 404
    assert exc_info.value.code == "project_not_found"


def test_delete_default_project_returns_bad_request(temp_service: DesktopApiService) -> None:
    with pytest.raises(ApiError) as exc_info:
        temp_service.delete_project("default")

    assert exc_info.value.status == 400
    assert exc_info.value.code == "invalid_request"
