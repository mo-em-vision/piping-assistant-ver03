"""API exposure of Flow Guidance Layer structured blocks."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
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


def test_api_task_state_exposes_guidance_and_transcript_blocks(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = service.get_task(task_id, session_id)
    flow_guidance = state.get("flow_guidance")
    assert isinstance(flow_guidance, dict)
    assert "presentation_blocks" in flow_guidance
    assert "transcript_blocks" in flow_guidance
    assert isinstance(flow_guidance["presentation_blocks"], list)
    assert isinstance(flow_guidance["transcript_blocks"], list)

    workflow_state = state["workflow_state"]
    assert "presentation_blocks" in workflow_state
    assert flow_guidance is not workflow_state


def test_mawp_task_state_exposes_guidance_without_formula_copy(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("mawp_design", session_id)
    task_id = created["task_id"]

    state = service.get_task(task_id, session_id)
    flow_guidance = state.get("flow_guidance") or {}
    blocks = flow_guidance.get("presentation_blocks") or []
    combined = " ".join(
        str(block.get("text") or block.get("content") or "")
        for block in blocks
        if isinstance(block, dict)
    ).lower()
    assert "mawp =" not in combined
    assert "2sewt" not in combined.replace(" ", "")
