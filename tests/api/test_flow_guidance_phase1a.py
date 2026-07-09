"""Phase 1A integration tests for durable flow_guidance.transcript_blocks."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from api.desktop_service import DesktopApiService
from api.flow_guidance_transcript import FLOW_GUIDANCE_TRANSCRIPT_KEY
from config.loader import CLIConfig
from engine.presentation.guidance_resolver import guidance_workflows_root
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


def _visible_text(state: dict) -> str:
    parts: list[str] = []
    for block in state.get("flow_guidance", {}).get("transcript_blocks") or []:
        if isinstance(block, dict):
            parts.append(str(block.get("text") or ""))
    for block in state.get("display_outputs") or []:
        if isinstance(block, dict):
            parts.append(str(block.get("content") or block.get("text") or ""))
    return " ".join(parts)


def test_guidance_yaml_entry_ids_unique_per_workflow() -> None:
    root = guidance_workflows_root()
    for path in sorted(root.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = payload.get("entries") or []
        ids = [str(entry.get("id")) for entry in entries if isinstance(entry, dict)]
        assert len(ids) == len(set(ids)), f"duplicate entry ids in {path.name}: {ids}"


def test_guidance_block_renders_once_in_transcript(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    state = service.submit_input(
        task_id,
        parameter="pressure_loading",
        value="internal_pressure",
        session_id=session_id,
    )
    transcript = state["flow_guidance"]["transcript_blocks"]
    guidance = [block for block in transcript if block.get("kind") == "guidance"]
    assert guidance
    assert len({block["block_id"] for block in guidance}) == len(guidance)
    assert any(
        str(block["block_id"]).endswith("pressure-loading-branch")
        for block in guidance
    )


def test_repeated_get_task_does_not_duplicate_transcript_blocks(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    first = service.get_task(task_id, session_id)
    second = service.get_task(task_id, session_id)

    first_blocks = first["flow_guidance"]["transcript_blocks"]
    second_blocks = second["flow_guidance"]["transcript_blocks"]
    assert first_blocks == second_blocks
    assert len({block["block_id"] for block in first_blocks}) == len(first_blocks)


def test_repeated_get_task_without_changes_does_not_save_again(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    service.get_task(task_id, session_id)

    with patch.object(service, "_save_manager") as save_mock:
        service.get_task(task_id, session_id)
        save_mock.assert_not_called()


def test_transcript_serialization_is_deterministic(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    first = service.get_task(task_id, session_id)
    second = service.get_task(task_id, session_id)

    assert first["flow_guidance"]["transcript_blocks"] == second["flow_guidance"]["transcript_blocks"]


def test_no_duplicate_block_id_in_center_panel_projection(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = service.get_task(task_id, session_id)
    transcript_ids = {
        block["block_id"]
        for block in state["flow_guidance"]["transcript_blocks"]
        if isinstance(block, dict) and block.get("block_id")
    }
    display_ids = {
        block["id"]
        for block in state.get("display_outputs") or []
        if isinstance(block, dict) and block.get("id")
    }
    overlap = transcript_ids & display_ids
    assert not overlap
    assert len(transcript_ids) == len(state["flow_guidance"]["transcript_blocks"])


def test_no_internal_planner_json_in_visible_center_panel_text(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = service.get_task(task_id, session_id)
    visible = _visible_text(state).lower()
    assert "engineering_plan" not in visible
    assert "legacy_goal_map" not in visible
    assert '"goal-' not in visible
    assert "waiting_user_input" not in visible


def test_reload_shows_one_guidance_block_not_zero_or_duplicate(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    service.submit_input(
        task_id,
        parameter="pressure_loading",
        value="internal_pressure",
        session_id=session_id,
    )
    reloaded = service.get_task(task_id, session_id)

    guidance = [
        block
        for block in reloaded["flow_guidance"]["transcript_blocks"]
        if block.get("kind") == "guidance"
    ]
    assert guidance
    assert len({block["block_id"] for block in guidance}) == len(guidance)


def test_display_outputs_still_present_after_transcript_sync(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = service.get_task(task_id, session_id)
    assert isinstance(state.get("display_outputs"), list)
    assert "center_panel_transcript" not in state


def test_flow_guidance_transcript_persisted_on_task_outputs(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    service.get_task(task_id, session_id)
    manager = service._store_for(session_id).load_state_manager()
    task = manager.get_task(task_id)
    stored = task.outputs.get(FLOW_GUIDANCE_TRANSCRIPT_KEY)
    assert isinstance(stored, list)
    assert len(stored) >= 1
    block_ids = {block.get("block_id") for block in stored}
    assert "workflow-intro-pipe_wall_thickness_design" in block_ids
