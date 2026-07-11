"""Phase 1B tests — workflow-node title/description and runtime result text in transcript."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
from api.flow_guidance_runtime_texts import (
    result_summary_block_id,
    runtime_transcript_candidates,
    workflow_description_block_id,
    workflow_intro_block_id,
    workflow_node_transcript_blocks,
    workflow_title_block_id,
)
from api.flow_guidance_transcript import FLOW_GUIDANCE_TRANSCRIPT_KEY
from config.loader import CLIConfig
from models.display_role import DisplayRole
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


def test_workflow_node_transcript_blocks_include_title_and_description_only_while_active(
    standards_reader,
) -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("phase1b-intro-only")
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = workflow_node_transcript_blocks(task, standards_reader)
    block_ids = {block.block_id for block in blocks}

    assert workflow_title_block_id("pipe_wall_thickness_design") in block_ids
    assert workflow_description_block_id("pipe_wall_thickness_design") in block_ids
    assert result_summary_block_id("pipe_wall_thickness_design") not in block_ids

    title = next(
        block
        for block in blocks
        if block.block_id == workflow_title_block_id("pipe_wall_thickness_design")
    )
    assert title.payload.get("display_role") == DisplayRole.title.value
    assert title.text == "Pipe Wall Thickness Design"

    description = next(
        block
        for block in blocks
        if block.block_id == workflow_description_block_id("pipe_wall_thickness_design")
    )
    assert description.payload.get("display_role") == DisplayRole.workflow_description.value
    assert "graph expansion" in (description.text or "").lower()


def test_runtime_transcript_candidates_include_result_when_completed() -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("phase1b-result", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = runtime_transcript_candidates(task)
    block_ids = {block.block_id for block in blocks}

    assert result_summary_block_id("pipe_wall_thickness_design") in block_ids
    assert workflow_title_block_id("pipe_wall_thickness_design") not in block_ids
    result = next(
        block
        for block in blocks
        if block.block_id == result_summary_block_id("pipe_wall_thickness_design")
    )
    assert result.payload.get("display_role") == DisplayRole.result_summary.value
    assert "Minimum required wall thickness" in (result.text or "")


def test_create_task_appends_workflow_title_and_description_once(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = service.get_task(task_id, session_id)
    transcript = state["flow_guidance"]["transcript_blocks"]
    title_blocks = [
        block
        for block in transcript
        if block.get("block_id") == workflow_title_block_id("pipe_wall_thickness_design")
    ]
    description_blocks = [
        block
        for block in transcript
        if block.get("block_id") == workflow_description_block_id("pipe_wall_thickness_design")
    ]
    assert len(title_blocks) == 1
    assert len(description_blocks) == 1
    assert title_blocks[0]["payload"]["display_role"] == DisplayRole.title.value
    assert description_blocks[0]["payload"]["display_role"] == DisplayRole.workflow_description.value


def test_repeated_get_task_does_not_duplicate_workflow_title(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    service.get_task(task_id, session_id)
    service.get_task(task_id, session_id)

    state = service.get_task(task_id, session_id)
    transcript = state["flow_guidance"]["transcript_blocks"]
    title_id = workflow_title_block_id("pipe_wall_thickness_design")
    title_blocks = [block for block in transcript if block.get("block_id") == title_id]
    assert len(title_blocks) == 1


def test_runtime_transcript_candidates_exclude_legacy_workflow_intro() -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("phase1b-no-legacy-intro")
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = runtime_transcript_candidates(task)
    block_ids = {block.block_id for block in blocks}
    assert workflow_intro_block_id("pipe_wall_thickness_design") not in block_ids
