"""API compatibility tests for legacy parameter key aliases."""

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


def test_design_pressure_submit_maps_to_canonical_pressure_fact(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Legacy design_pressure submit must store the canonical pressure fact key."""
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        unit=None,
        session_id=session_id,
    )
    service.submit_input(
        task_id,
        parameter="pressure_loading",
        value="internal_pressure",
        unit=None,
        session_id=session_id,
    )
    state = service.submit_input(
        task_id,
        parameter="design_pressure",
        value=8.0,
        unit="bar",
        session_id=session_id,
    )

    facts = state.get("facts") or {}
    assert "internal_design_gage_pressure" in facts
    assert facts["internal_design_gage_pressure"].get("display_value") is not None
