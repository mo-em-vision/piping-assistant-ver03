"""Sync durable Flow Guidance transcript blocks onto task presentation state."""

from __future__ import annotations

import os

from engine.reference.standards_reader import StandardsReader
from models.presentation import presentation_block_from_dict
from models.task import Task

from api.flow_guidance import build_flow_guidance_payload
from api.flow_guidance_transcript import (
    is_guidance_narration_block,
    load_flow_guidance_transcript_blocks,
    merge_guidance_into_transcript,
    presentation_block_to_canonical_guidance,
    save_flow_guidance_transcript,
    transcript_is_frozen,
)
from api.flow_guidance_runtime_texts import runtime_transcript_candidates, workflow_node_transcript_blocks


def _transcript_sync_enabled() -> bool:
    return os.environ.get("FLOW_GUIDANCE_TRANSCRIPT_ENABLED", "1") != "0"


def _workflow_id_for_task(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")


def _current_guidance_presentation_blocks(
    task: Task,
    reader: StandardsReader,
) -> tuple:
    payload = build_flow_guidance_payload(task, reader, transcript_blocks=())
    presentation = payload.get("presentation_blocks") or []
    blocks = []
    for raw in presentation:
        if isinstance(raw, dict) and is_guidance_narration_block(raw):
            blocks.append(presentation_block_from_dict(raw))
    return tuple(blocks)


def sync_flow_guidance_transcript(
    task: Task,
    reader: StandardsReader,
) -> tuple[Task, bool]:
    """Append or update guidance narration in task.outputs flow_guidance_transcript."""
    if not _transcript_sync_enabled():
        return task, False

    workflow_id = _workflow_id_for_task(task)
    if not workflow_id:
        return task, False

    stored = load_flow_guidance_transcript_blocks(task)
    guidance_blocks = _current_guidance_presentation_blocks(task, reader)
    normalized = tuple(
        presentation_block_to_canonical_guidance(block, workflow_id)
        for block in guidance_blocks
    )
    runtime_blocks = runtime_transcript_candidates(task)
    workflow_blocks = workflow_node_transcript_blocks(task, reader)
    candidates = normalized + workflow_blocks + runtime_blocks

    merged, changed = merge_guidance_into_transcript(
        stored,
        candidates,
        frozen=transcript_is_frozen(task),
    )
    if not changed:
        return task, False

    save_flow_guidance_transcript(task, merged)
    return task, True
