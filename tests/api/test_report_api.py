"""Tests for desktop report API."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
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


def test_get_task_report_status(temp_service: DesktopApiService, standards_reader, state_manager) -> None:
    session_id = api_session_id(temp_service)
    task_id = "pipe-wall-thickness-desi-report01"
    run_completed_workflow(state_manager, standards_reader, task_id)
    temp_service._save_manager(state_manager, session_id)

    status = temp_service.get_task_report(task_id, session_id)
    assert status["task_id"] == task_id
    assert status["title"]
    assert "files" in status


def test_generate_and_preview_report(temp_service: DesktopApiService, standards_reader, state_manager) -> None:
    session_id = api_session_id(temp_service)
    task_id = "pipe-wall-thickness-desi-report02"
    run_completed_workflow(state_manager, standards_reader, task_id)
    temp_service._save_manager(state_manager, session_id)

    generated = temp_service.generate_task_report(task_id, report_format="html", session_id=session_id)
    assert generated["generation_status"] == "ready"
    assert generated["files"]["html"]["available"] is True
    assert generated["files"]["pdf"]["available"] is True

    preview = temp_service.preview_task_report(task_id, preview_format="html", session_id=session_id)
    assert "Purpose" in preview["content"] or generated["title"] in preview["content"]

    file_path, content_type = temp_service.download_task_report(
        task_id,
        download_format="html",
        session_id=session_id,
    )
    assert file_path.exists()
    assert "html" in content_type

    pdf_path, pdf_content_type = temp_service.download_task_report(
        task_id,
        download_format="pdf",
        session_id=session_id,
    )
    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:5] == b"%PDF-"
    assert "pdf" in pdf_content_type


def test_generate_pdf_report(temp_service: DesktopApiService, standards_reader, state_manager) -> None:
    session_id = api_session_id(temp_service)
    task_id = "pipe-wall-thickness-desi-report03"
    run_completed_workflow(state_manager, standards_reader, task_id)
    temp_service._save_manager(state_manager, session_id)

    generated = temp_service.generate_task_report(task_id, report_format="pdf", session_id=session_id)
    assert generated["generation_status"] == "ready"
    assert generated["files"]["pdf"]["available"] is True

    file_path, content_type = temp_service.download_task_report(
        task_id,
        download_format="pdf",
        session_id=session_id,
    )
    assert file_path.exists()
    assert file_path.read_bytes()[:5] == b"%PDF-"
    assert "pdf" in content_type
