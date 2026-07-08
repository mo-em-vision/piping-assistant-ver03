"""Workflow regression tests for compact submit_input responses."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from tests.api.conftest import api_session_id


def _service() -> tuple[DesktopApiService, str]:
    os.environ["DEV_INSPECTION_ENABLED"] = "1"
    project_root = Path(__file__).resolve().parents[2]
    tmpdir = tempfile.mkdtemp()
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=Path(tmpdir),
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    service = DesktopApiService(config=config, session_id="default")
    session_id = api_session_id(service, "Submit Workflow Regression")
    return service, session_id


def _assert_compact_task_state(state: dict) -> None:
    assert "engineering_plan" not in state
    assert "engineering_plan_view" not in state
    assert "legacy_goal_map" not in state
    assert "canonical" not in state
    assert "inspector_summary" not in state
    assert isinstance(state.get("parameters"), list)
    assert isinstance(state.get("display_outputs"), list)
    assert isinstance(state.get("flow_guidance"), dict)
    assert isinstance(state.get("progress"), dict)


def test_pipe_wall_pressure_loading_advances_with_compact_task_state() -> None:
    service, session_id = _service()
    state = service.create_task("pipe_wall_thickness_design", session_id=session_id)
    task_id = state["task_id"]

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    _assert_compact_task_state(state)

    state = service.submit_input(
        task_id,
        parameter="pressure_loading",
        value="internal_pressure",
        session_id=session_id,
    )
    _assert_compact_task_state(state)

    timeline = state["progress"]["timeline"]
    straight = next(step for step in timeline if step["id"] == "straight_pipe_section")
    pressure = next(step for step in timeline if step["id"] == "pressure_loading")
    assert straight["status"] == "done"
    assert pressure["status"] == "done"
    assert pressure.get("display_value")

    follow_up = service.get_task(task_id, session_id=session_id)
    _assert_compact_task_state(follow_up)
    assert follow_up["progress"]["timeline"][1]["status"] == "done"


def test_submit_is_compact_while_inspection_remains_full_debug() -> None:
    service, session_id = _service()
    created = service.create_task("pipe_wall_thickness_design", session_id=session_id)
    task_id = created["task_id"]

    submit_state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    _assert_compact_task_state(submit_state)

    inspection = service.get_inspection(task_id, session_id)
    assert isinstance(inspection.get("engineering_plan"), dict)
    assert isinstance(inspection.get("planner_inspector_summary"), dict)
    assert isinstance(inspection.get("legacy_goal_map"), dict)
    assert isinstance(inspection.get("canonical_task_state"), dict)
    assert isinstance(inspection.get("task_state_views"), dict)
