"""Phase 1B tests — runtime.yaml initiation/result text in durable transcript."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
from api.flow_guidance_runtime_texts import (
    result_summary_block_id,
    runtime_transcript_candidates,
    workflow_intro_block_id,
)
from api.flow_guidance_transcript import FLOW_GUIDANCE_TRANSCRIPT_KEY
from config.loader import CLIConfig
from models.task import TaskStatus
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


def test_runtime_transcript_candidates_include_intro_only_while_active() -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("phase1b-intro-only")
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = runtime_transcript_candidates(task)
    block_ids = {block.block_id for block in blocks}

    assert workflow_intro_block_id("pipe_wall_thickness_design") in block_ids
    assert result_summary_block_id("pipe_wall_thickness_design") not in block_ids
    intro = next(
        block
        for block in blocks
        if block.block_id == workflow_intro_block_id("pipe_wall_thickness_design")
    )
    assert intro.payload.get("display_role") == "workflow_intro"
    assert "Pipe Wall Thickness Design" in (intro.text or "")


def test_runtime_transcript_candidates_include_result_when_completed() -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("phase1b-result", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = runtime_transcript_candidates(task)
    block_ids = {block.block_id for block in blocks}

    assert result_summary_block_id("pipe_wall_thickness_design") in block_ids
    result = next(
        block
        for block in blocks
        if block.block_id == result_summary_block_id("pipe_wall_thickness_design")
    )
    assert result.payload.get("display_role") == "result_summary"
    assert "Minimum required wall thickness" in (result.text or "")


def test_create_task_appends_workflow_intro_once(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = service.get_task(task_id, session_id)
    transcript = state["flow_guidance"]["transcript_blocks"]
    intro_blocks = [
        block
        for block in transcript
        if block.get("block_id") == workflow_intro_block_id("pipe_wall_thickness_design")
    ]
    assert len(intro_blocks) == 1
    assert intro_blocks[0]["kind"] == "text"
    assert intro_blocks[0]["source"] == "runtime"
    assert intro_blocks[0]["payload"]["display_role"] == "workflow_intro"


def test_repeated_get_task_does_not_duplicate_workflow_intro(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    first = service.get_task(task_id, session_id)
    second = service.get_task(task_id, session_id)

    intro_id = workflow_intro_block_id("pipe_wall_thickness_design")
    first_intro = [block for block in first["flow_guidance"]["transcript_blocks"] if block.get("block_id") == intro_id]
    second_intro = [block for block in second["flow_guidance"]["transcript_blocks"] if block.get("block_id") == intro_id]
    assert len(first_intro) == 1
    assert first_intro == second_intro


def test_completed_task_appends_result_summary_once(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(task_id)
    task.status = TaskStatus.COMPLETED
    manager.replace_task(task_id, task)
    store.save_state_manager(manager)

    state = service.get_task(task_id, session_id)
    transcript = state["flow_guidance"]["transcript_blocks"]
    result_id = result_summary_block_id("pipe_wall_thickness_design")
    result_blocks = [block for block in transcript if block.get("block_id") == result_id]
    assert len(result_blocks) == 1
    assert result_blocks[0]["payload"]["display_role"] == "result_summary"

    manager = store.load_state_manager()
    stored = manager.get_task(task_id).outputs.get(FLOW_GUIDANCE_TRANSCRIPT_KEY) or []
    stored_results = [block for block in stored if block.get("block_id") == result_id]
    assert len(stored_results) == 1
