"""Phase 1B tests — workflow-node title/description and runtime result text in transcript."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
from api.flow_guidance_runtime_texts import (
    result_summary_block_id,
    workflow_intro_block_id,
    workflow_node_transcript_blocks,
)
from api.output_blocks import build_display_outputs
from api.result_summary_display import build_result_summary_display_block
from api.flow_guidance_transcript import FLOW_GUIDANCE_TRANSCRIPT_KEY, load_flow_guidance_transcript_blocks
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


def test_workflow_node_transcript_blocks_emit_workflow_intro_only_while_active(
    standards_reader,
) -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("phase1b-intro-only")
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = workflow_node_transcript_blocks(task, standards_reader)
    block_ids = {block.block_id for block in blocks}

    assert workflow_intro_block_id("pipe_wall_thickness_design") in block_ids
    assert result_summary_block_id("pipe_wall_thickness_design") not in block_ids
    assert len(blocks) == 1

    intro = blocks[0]
    assert intro.payload.get("display_role") == DisplayRole.workflow_intro.value
    assert intro.payload.get("title") == "Pipe Wall Thickness Design"
    assert intro.text.startswith("Pipe Wall Thickness Design")
    assert "graph expansion" in (intro.text or "").lower()


def test_completed_task_result_summary_comes_from_display_outputs_only(
    standards_reader,
) -> None:
    from engine.state.state_manager import TaskStateManager
    from tests.api.test_equation_display_trace import _apply_simulated_completed_state

    manager = TaskStateManager()
    task = manager.create_task("phase1b-result", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    _apply_simulated_completed_state(task, standards_reader)

    transcript_block_ids = {
        block.block_id for block in load_flow_guidance_transcript_blocks(task)
    }
    assert result_summary_block_id("pipe_wall_thickness_design") not in transcript_block_ids

    summary = build_result_summary_display_block(task, standards_reader)
    assert summary is not None
    assert summary["id"] == result_summary_block_id("pipe_wall_thickness_design")
    assert summary["display_role"] == DisplayRole.result_summary.value
    assert "selected branch" in str(summary.get("content") or "")
    assert summary.get("payload", {}).get("applied_paragraphs")

    display_blocks = build_display_outputs(task, reader=standards_reader)
    result_blocks = [
        block
        for block in display_blocks
        if block.get("id") == result_summary_block_id("pipe_wall_thickness_design")
    ]
    assert len(result_blocks) == 1


def test_create_task_appends_workflow_intro_once(
    tmp_path: Path,
    project_root: Path,
) -> None:
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
    assert intro_blocks[0]["payload"]["display_role"] == DisplayRole.workflow_intro.value


def test_repeated_get_task_does_not_duplicate_workflow_intro(
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
    intro_id = workflow_intro_block_id("pipe_wall_thickness_design")
    intro_blocks = [block for block in transcript if block.get("block_id") == intro_id]
    assert len(intro_blocks) == 1


def test_workflow_node_transcript_blocks_emit_workflow_intro(
    standards_reader,
) -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("phase1b-no-legacy-intro")
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = workflow_node_transcript_blocks(task, standards_reader)
    block_ids = {block.block_id for block in blocks}
    assert workflow_intro_block_id("pipe_wall_thickness_design") in block_ids
    assert result_summary_block_id("pipe_wall_thickness_design") not in block_ids
