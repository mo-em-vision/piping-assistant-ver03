"""Tests for project API endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig


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


def test_create_and_list_projects(temp_service: DesktopApiService) -> None:
    assert temp_service.list_projects() == []
    created = temp_service.create_project("Offshore Platform B")
    projects = temp_service.list_projects()

    assert created["name"] == "Offshore Platform B"
    assert any(project["id"] == created["id"] for project in projects)


def test_activate_project_returns_session_id(temp_service: DesktopApiService) -> None:
    created = temp_service.create_project("Tank Farm")
    activated = temp_service.activate_project(created["id"])

    assert activated["session_id"] == created["id"]
    assert activated["project"]["name"] == "Tank Farm"


def test_tasks_are_scoped_to_project(temp_service: DesktopApiService) -> None:
    project_a = temp_service.create_project("Project A")
    project_b = temp_service.create_project("Project B")

    temp_service.create_task("pipe_wall_thickness_design", project_a["id"])
    temp_service.create_task("pipe_wall_thickness_design", project_b["id"])

    tasks_a = temp_service.list_tasks(project_a["id"])
    tasks_b = temp_service.list_tasks(project_b["id"])

    assert len(tasks_a["tasks"]) == 1
    assert len(tasks_b["tasks"]) == 1
    assert tasks_a["tasks"][0]["id"] != tasks_b["tasks"][0]["id"]
