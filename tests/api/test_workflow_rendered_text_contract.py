"""Contract tests for workflow rendered text and block output (audit)."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.center_panel_contract import assemble_center_panel_scroll_blocks
from api.desktop_service import DesktopApiService
from api.flow_guidance_runtime_texts import (
    workflow_description_block_id,
    workflow_node_transcript_blocks,
    workflow_title_block_id,
)
from api.output_blocks import build_display_outputs
from api.paragraph_display import build_paragraph_display_block
from api.serializers import WORKFLOW_CATALOG
from api.workflow_display import workflow_display_meta
from config.loader import CLIConfig
from engine.messaging.center_panel_copy import GENERIC_INPUT_WAITING_MESSAGE
from engine.planner.workflow_goal_metadata import (
    workflow_display_description_from_node,
    workflow_display_title_from_node,
)
from engine.reference.standards_reader import StandardsReader
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


def test_workflow_title_and_description_from_workflow_node(standards_reader) -> None:
    workflow_id = "pipe_wall_thickness_design"
    title = workflow_display_title_from_node(standards_reader, workflow_id)
    description = workflow_display_description_from_node(standards_reader, workflow_id)

    assert title == "Pipe Wall Thickness Design"
    assert "graph expansion" in description.lower()

    catalog_entry = next(item for item in WORKFLOW_CATALOG if item["id"] == workflow_id)
    meta = workflow_display_meta(workflow_id, catalog_entry, reader=standards_reader)
    assert meta["display_title"] == title
    assert meta["subtitle"] == description
    assert meta["display_title"] != catalog_entry["display_title"] or title == catalog_entry["display_title"]


def test_workflow_node_transcript_blocks_emit_title_and_description(
    standards_reader,
) -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("contract-title-description")
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = workflow_node_transcript_blocks(task, standards_reader)
    block_ids = {block.block_id for block in blocks}

    assert workflow_title_block_id("pipe_wall_thickness_design") in block_ids
    assert workflow_description_block_id("pipe_wall_thickness_design") in block_ids

    title_block = next(
        block
        for block in blocks
        if block.block_id == workflow_title_block_id("pipe_wall_thickness_design")
    )
    description_block = next(
        block
        for block in blocks
        if block.block_id == workflow_description_block_id("pipe_wall_thickness_design")
    )

    assert title_block.source == "workflow_node"
    assert title_block.payload.get("display_role") == DisplayRole.title.value
    assert title_block.text == "Pipe Wall Thickness Design"

    assert description_block.source == "workflow_node"
    assert description_block.payload.get("display_role") == DisplayRole.workflow_description.value
    assert "graph expansion" in (description_block.text or "").lower()


def test_create_task_transcript_includes_workflow_node_title_and_description(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    state = service.get_task(task_id, session_id)
    transcript = state["flow_guidance"]["transcript_blocks"]
    block_ids = {block["block_id"] for block in transcript if isinstance(block, dict)}

    assert workflow_title_block_id("pipe_wall_thickness_design") in block_ids
    assert workflow_description_block_id("pipe_wall_thickness_design") in block_ids

    title_blocks = [
        block
        for block in transcript
        if block.get("block_id") == workflow_title_block_id("pipe_wall_thickness_design")
    ]
    assert len(title_blocks) == 1
    assert title_blocks[0]["payload"]["display_role"] == DisplayRole.title.value


def test_paragraph_without_presentation_summary_emits_no_block(standards_reader) -> None:
    block = build_paragraph_display_block(standards_reader, "paragraph-without-presentation-summary")
    assert block is None


def test_awaiting_input_emits_generic_input_waiting_block(
    tmp_path: Path,
    project_root: Path,
    standards_reader,
) -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("contract-input-waiting", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = build_display_outputs(task, reader=standards_reader)
    waiting = [block for block in blocks if block.get("id") == "input-waiting"]
    assert len(waiting) == 1
    assert waiting[0]["display_role"] == DisplayRole.input_waiting.value
    assert waiting[0]["content"] == GENERIC_INPUT_WAITING_MESSAGE
    assert "PARAM-" not in waiting[0]["content"]
    assert waiting[0]["lifecycle"] == "volatile"


def test_input_waiting_block_absent_after_task_completes(
    tmp_path: Path,
    project_root: Path,
    standards_reader,
) -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("contract-no-waiting", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    blocks = build_display_outputs(task, reader=standards_reader)
    assert "input-waiting" not in {block.get("id") for block in blocks}


def test_center_panel_scroll_orders_title_before_description(
    standards_reader,
) -> None:
    from engine.state.state_manager import TaskStateManager

    manager = TaskStateManager()
    task = manager.create_task("contract-scroll-order")
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    transcript = [
        {
            "block_id": block.block_id,
            "kind": block.kind,
            "source": block.source,
            "text": block.text,
            "payload": block.payload,
        }
        for block in workflow_node_transcript_blocks(task, standards_reader)
    ]

    scroll = assemble_center_panel_scroll_blocks(
        transcript_blocks=transcript,
        display_outputs=[],
    )
    roles = [block.get("display_role") for block in scroll]
    assert roles.index(DisplayRole.title.value) < roles.index(DisplayRole.workflow_description.value)
