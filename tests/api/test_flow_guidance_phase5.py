"""Phase 5 integration tests — durable next_workflows on task completion."""

from __future__ import annotations

from pathlib import Path

from api.completion_next_workflows_transcript import (
    append_completion_next_workflows_transcript,
    build_next_workflows_block,
    load_runtime_suggested_workflow_ids,
    next_workflows_block_id,
)
from api.desktop_service import DesktopApiService
from api.flow_guidance_transcript import FLOW_GUIDANCE_TRANSCRIPT_KEY, load_flow_guidance_transcript_blocks
from config.loader import CLIConfig
from engine.state.state_manager import TaskStateManager
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


def _next_workflow_blocks(transcript: list[dict]) -> list[dict]:
    return [
        block
        for block in transcript
        if isinstance(block, dict) and block.get("kind") == "next_workflows"
    ]


def test_pipe_wall_runtime_lists_mawp_suggestion() -> None:
    suggested = load_runtime_suggested_workflow_ids("pipe_wall_thickness_design")
    assert "mawp_design" in suggested


def test_build_next_workflows_block_uses_catalog_metadata(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pw-complete", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    block = build_next_workflows_block(task, standards_reader)
    assert block is not None
    suggestions = block.payload.get("suggestions") or []
    assert len(suggestions) == 1
    assert suggestions[0]["workflow_id"] == "mawp_design"
    assert suggestions[0]["title"]
    assert "mawp" in suggestions[0]["title"].lower() or "mawp" in suggestions[0]["workflow_id"]


def test_append_is_idempotent(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pw-idempotent", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    task, first_changed = append_completion_next_workflows_transcript(task, standards_reader)
    assert first_changed is True
    stored_after_first = load_flow_guidance_transcript_blocks(task)

    task, second_changed = append_completion_next_workflows_transcript(task, standards_reader)
    assert second_changed is False
    stored_after_second = load_flow_guidance_transcript_blocks(task)
    assert len(stored_after_first) == len(stored_after_second) == 1


def test_no_block_when_runtime_has_no_suggestions(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("no-suggestions", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "nonexistent_workflow_slug_xyz"

    block = build_next_workflows_block(task, standards_reader)
    assert block is None


def test_block_id_is_stable_and_unique(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pw-block-id", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    expected = next_workflows_block_id(task.task_id, "pipe_wall_thickness_design")
    block = build_next_workflows_block(task, standards_reader)
    assert block is not None
    assert block.block_id == expected
    assert expected.startswith("next-workflows-")


def test_completed_task_get_task_appends_once_via_repair(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(task_id)
    task.status = TaskStatus.COMPLETED
    manager.replace_task(task_id, task)
    store.save_state_manager(manager)

    first = service.get_task(task_id, session_id)
    second = service.get_task(task_id, session_id)

    first_blocks = _next_workflow_blocks(first["flow_guidance"]["transcript_blocks"])
    second_blocks = _next_workflow_blocks(second["flow_guidance"]["transcript_blocks"])
    assert len(first_blocks) == 1
    assert first_blocks == second_blocks
    assert first_blocks[0]["block_id"] == next_workflows_block_id(task_id, "pipe_wall_thickness_design")
    suggestions = first_blocks[0].get("suggestions") or []
    assert any(item.get("workflow_id") == "mawp_design" for item in suggestions)


def test_next_workflows_not_persisted_with_flattened_only_fields(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(task_id)
    task.status = TaskStatus.COMPLETED
    manager.replace_task(task_id, task)
    store.save_state_manager(manager)
    service.get_task(task_id, session_id)

    manager = store.load_state_manager()
    task = manager.get_task(task_id)
    raw = task.outputs.get(FLOW_GUIDANCE_TRANSCRIPT_KEY) or []
    assert isinstance(raw, list)
    stored_next = [item for item in raw if isinstance(item, dict) and item.get("kind") == "next_workflows"]
    assert len(stored_next) == 1
    assert "suggestions" in (stored_next[0].get("payload") or stored_next[0])


def test_build_path_does_not_import_task_continuation_agent() -> None:
    import api.completion_next_workflows_transcript as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "TaskContinuationAgent" not in source
    assert "task_continuation" not in source


def test_phase1_through_phase4_guard_modules_importable() -> None:
    import tests.api.test_flow_guidance_phase1a  # noqa: F401
    import tests.api.test_flow_guidance_phase2  # noqa: F401
    import tests.api.test_flow_guidance_phase3  # noqa: F401
    import tests.api.test_equation_row_provenance  # noqa: F401
