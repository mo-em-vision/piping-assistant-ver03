"""Tests for task continuation suggestions API."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import ApiError, DesktopApiService
from config.loader import CLIConfig
from tests.acceptance.helpers import run_completed_workflow
from tests.api.conftest import api_session_id


@pytest.fixture
def temp_service(tmp_path: Path) -> DesktopApiService:
    sessions_dir = tmp_path / "sessions"
    standards_root = Path(__file__).resolve().parents[2] / "standards"
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=sessions_dir,
        standards_root=standards_root,
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def test_continuation_suggestions_for_completed_task(
    temp_service: DesktopApiService,
    standards_reader,
    state_manager,
) -> None:
    session_id = api_session_id(temp_service)
    task_id = "pipe-wall-thickness-desi-cont01"
    run_completed_workflow(state_manager, standards_reader, task_id)
    temp_service._save_manager(state_manager, session_id)

    payload = temp_service.get_task_continuation_suggestions(task_id, session_id)

    assert payload["task_id"] == task_id
    assert payload["workflow_id"]
    assert len(payload["suggestions"]) >= 2
    first = payload["suggestions"][0]
    assert first["id"]
    assert first["title"]
    assert first["description"]


def test_continuation_suggestions_rejects_incomplete_task(
    temp_service: DesktopApiService,
) -> None:
    session_id = api_session_id(temp_service)
    created = temp_service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    with pytest.raises(ApiError) as exc_info:
        temp_service.get_task_continuation_suggestions(task_id, session_id)

    assert exc_info.value.status == 409
    assert exc_info.value.code == "task_not_completed"


def test_continuation_suggestions_task_not_found(temp_service: DesktopApiService) -> None:
    session_id = api_session_id(temp_service)

    with pytest.raises(ApiError) as exc_info:
        temp_service.get_task_continuation_suggestions("missing-task", session_id)

    assert exc_info.value.status == 404
