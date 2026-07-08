"""Unit tests for flow guidance transcript persistence helpers."""

from __future__ import annotations

from models.presentation import PresentationBlock
from models.task import Task, TaskStatus, new_task

from api.flow_guidance_transcript import (
    FLOW_GUIDANCE_TRANSCRIPT_KEY,
    guidance_transcript_block_id,
    load_flow_guidance_transcript_blocks,
    merge_guidance_into_transcript,
    presentation_block_to_canonical_guidance,
    serialize_transcript_blocks,
)


def _task() -> Task:
    return new_task("task-1", status=TaskStatus.AWAITING_INPUT, workflow_id="pipe_wall_thickness_design")


def _guidance_block(entry_id: str, text: str) -> PresentationBlock:
    return PresentationBlock(
        block_id=entry_id,
        kind="guidance",
        source="guidance",
        text=text,
    )


def test_guidance_transcript_block_id_uses_workflow_slug() -> None:
    block_id = guidance_transcript_block_id("pipe-wall-thickness-design", "expansion-gate-intro")
    assert block_id == "guidance-pipe_wall_thickness_design-expansion-gate-intro"


def test_merge_guidance_appends_once_and_updates_in_place() -> None:
    workflow_id = "pipe_wall_thickness_design"
    first = presentation_block_to_canonical_guidance(
        _guidance_block("expansion-gate-intro", "First text"),
        workflow_id,
    )
    merged, changed = merge_guidance_into_transcript((), (first,), frozen=False)
    assert changed is True
    assert len(merged) == 1

    merged_again, changed_again = merge_guidance_into_transcript(merged, (first,), frozen=False)
    assert changed_again is False
    assert merged_again == merged

    updated = presentation_block_to_canonical_guidance(
        _guidance_block("expansion-gate-intro", "Updated text"),
        workflow_id,
    )
    merged_updated, changed_updated = merge_guidance_into_transcript(
        merged,
        (updated,),
        frozen=False,
    )
    assert changed_updated is True
    assert merged_updated[0].text == "Updated text"
    assert len(merged_updated) == 1


def test_merge_guidance_frozen_after_completion() -> None:
    workflow_id = "pipe_wall_thickness_design"
    stored = presentation_block_to_canonical_guidance(
        _guidance_block("expansion-gate-intro", "Frozen text"),
        workflow_id,
    )
    updated = presentation_block_to_canonical_guidance(
        _guidance_block("expansion-gate-intro", "Should not apply"),
        workflow_id,
    )
    merged, changed = merge_guidance_into_transcript((stored,), (updated,), frozen=True)
    assert changed is False
    assert merged[0].text == "Frozen text"


def test_load_and_serialize_transcript_blocks_from_task_outputs() -> None:
    task = _task()
    block = presentation_block_to_canonical_guidance(
        _guidance_block("expansion-gate-intro", "Persist me"),
        "pipe_wall_thickness_design",
    )
    task.outputs[FLOW_GUIDANCE_TRANSCRIPT_KEY] = [block.to_dict()]

    loaded = load_flow_guidance_transcript_blocks(task)
    assert len(loaded) == 1
    assert loaded[0].block_id == block.block_id

    first = serialize_transcript_blocks(loaded)
    second = serialize_transcript_blocks(loaded)
    assert first == second


def test_transcript_is_frozen_only_when_completed() -> None:
    from api.flow_guidance_transcript import transcript_is_frozen

    task = _task()
    assert transcript_is_frozen(task) is False
    task.status = TaskStatus.COMPLETED
    assert transcript_is_frozen(task) is True
