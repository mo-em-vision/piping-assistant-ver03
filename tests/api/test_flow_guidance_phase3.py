"""Phase 3 integration tests — reference chip projection on API payloads."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
from api.flow_guidance_transcript import FLOW_GUIDANCE_TRANSCRIPT_KEY, load_flow_guidance_transcript_blocks
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


def test_guidance_transcript_blocks_include_reference_chips(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)

    transcript = state["flow_guidance"]["transcript_blocks"]
    guidance = [
        block
        for block in transcript
        if isinstance(block, dict) and block.get("kind") == "guidance" and block.get("refs")
    ]
    assert guidance
    chips = guidance[0].get("reference_chips") or []
    assert chips
    assert chips[0]["label"] != chips[0]["id"]
    assert not str(chips[0]["label"]).startswith("304.1.1-a")


def test_reference_chips_are_not_persisted_on_task_outputs(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    service.get_task(task_id, session_id)

    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(task_id)
    stored_blocks = load_flow_guidance_transcript_blocks(task)
    assert stored_blocks
    for block in stored_blocks:
        assert "reference_chips" not in block.to_dict()

    raw = task.outputs.get(FLOW_GUIDANCE_TRANSCRIPT_KEY) or []
    for item in raw:
        if isinstance(item, dict):
            assert "reference_chips" not in item


def test_enrichment_preserves_transcript_block_ids_and_order(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    first = service.get_task(task_id, session_id)
    second = service.get_task(task_id, session_id)

    first_ids = [block["block_id"] for block in first["flow_guidance"]["transcript_blocks"]]
    second_ids = [block["block_id"] for block in second["flow_guidance"]["transcript_blocks"]]
    assert first_ids == second_ids
    assert len(first_ids) == len(set(first_ids))


def test_phase2_archives_still_present_after_chip_enrichment(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )

    archives = [
        block
        for block in state["flow_guidance"]["transcript_blocks"]
        if isinstance(block, dict) and block.get("source") == "input_archive"
    ]
    assert len(archives) == 2
