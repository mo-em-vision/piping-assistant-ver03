"""API tests for developer inspection endpoints."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService, ApiError
from config.loader import CLIConfig
from tests.api.conftest import api_session_id


def _service(tmp_path: Path, project_root: Path) -> DesktopApiService:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def test_inspection_disabled_returns_not_found(tmp_path: Path, project_root: Path) -> None:
    os.environ.pop("DEV_INSPECTION_ENABLED", None)
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    with pytest.raises(ApiError) as exc:
        service.get_inspection(created["task_id"], session_id)
    assert exc.value.status == 404


def test_inspection_enabled_returns_payload(tmp_path: Path, project_root: Path) -> None:
    os.environ["DEV_INSPECTION_ENABLED"] = "1"
    try:
        service = _service(tmp_path, project_root)
        session_id = api_session_id(service)
        created = service.create_task("pipe_wall_thickness_design", session_id)
        payload = service.get_inspection(created["task_id"], session_id)
        assert payload["task_id"] == created["task_id"]
        assert "execution_trace" in payload
        assert "planner_decisions" in payload
        assert "provenance_index" in payload
        assert "replay_frames" in payload
        assert "integrity_checks" in payload
        assert "performance" in payload
    finally:
        os.environ.pop("DEV_INSPECTION_ENABLED", None)
