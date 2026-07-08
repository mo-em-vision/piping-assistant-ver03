"""Task-scoped durable Flow Guidance transcript (presentation state only)."""

from __future__ import annotations

import json
import re
from typing import Any

from models.presentation import PresentationBlock, presentation_block_from_dict
from models.task import Task, TaskStatus

FLOW_GUIDANCE_TRANSCRIPT_KEY = "flow_guidance_transcript"
_GUIDANCE_BLOCK_ID_PREFIX = "guidance-"


def normalize_workflow_slug(workflow_id: str) -> str:
    return workflow_id.strip().replace("-", "_").lower()


def guidance_transcript_block_id(workflow_id: str, entry_id: str) -> str:
    slug = normalize_workflow_slug(workflow_id)
    cleaned_entry = str(entry_id).strip()
    return f"{_GUIDANCE_BLOCK_ID_PREFIX}{slug}-{cleaned_entry}"


def _entry_id_from_block_id(workflow_id: str, block_id: str) -> str:
    slug = normalize_workflow_slug(workflow_id)
    prefix = f"{_GUIDANCE_BLOCK_ID_PREFIX}{slug}-"
    if block_id.startswith(prefix):
        return block_id[len(prefix) :]
    if block_id.startswith(_GUIDANCE_BLOCK_ID_PREFIX):
        return re.sub(rf"^{_GUIDANCE_BLOCK_ID_PREFIX}[^-]+-", "", block_id, count=1)
    return block_id


def _display_role_for_entry(entry_id: str) -> str:
    if entry_id.startswith("input-context-") or "parameter-gathering" in entry_id or entry_id.endswith(
        "parameter_gathering"
    ):
        return "input_context"
    return "branch_narration"


def is_guidance_narration_block(data: dict[str, Any]) -> bool:
    return str(data.get("kind") or "") == "guidance" and str(data.get("source") or "") == "guidance"


def is_input_archive_block(data: dict[str, Any]) -> bool:
    source = str(data.get("source") or "")
    kind = str(data.get("kind") or "")
    return source == "input_archive" and kind in {"ask_archive", "answer_archive"}


def is_next_workflows_transcript_block(data: dict[str, Any]) -> bool:
    from api.completion_next_workflows_transcript import is_next_workflows_block

    return is_next_workflows_block(data)


def archive_ask_block_id(parameter_id: str, submission_id: str) -> str:
    return f"archived-ask-{parameter_id}-{submission_id}"


def archive_answer_block_id(parameter_id: str, submission_id: str) -> str:
    return f"archived-answer-{parameter_id}-{submission_id}"


def presentation_block_to_canonical_guidance(
    block: PresentationBlock,
    workflow_id: str,
) -> PresentationBlock:
    entry_id = _entry_id_from_block_id(workflow_id, block.block_id)
    canonical_id = guidance_transcript_block_id(workflow_id, entry_id)
    payload = dict(block.payload)
    payload.setdefault("display_role", _display_role_for_entry(entry_id))
    return PresentationBlock(
        block_id=canonical_id,
        kind=block.kind,
        source=block.source,
        text=block.text,
        refs=dict(block.refs),
        payload=payload,
    )


def _coerce_transcript_raw(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def load_flow_guidance_transcript_blocks(task: Task) -> tuple[PresentationBlock, ...]:
    """Load persisted guidance transcript blocks from task presentation state."""
    raw = task.outputs.get(FLOW_GUIDANCE_TRANSCRIPT_KEY)
    blocks: list[PresentationBlock] = []
    for item in _coerce_transcript_raw(raw):
        try:
            blocks.append(presentation_block_from_dict(item))
        except (KeyError, TypeError):
            continue
    return tuple(blocks)


def serialize_transcript_blocks(blocks: tuple[PresentationBlock, ...]) -> str:
    """Deterministic JSON for equality checks."""
    payload = [block.to_dict() for block in blocks]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def merge_append_only_blocks(
    stored: tuple[PresentationBlock, ...],
    new_blocks: tuple[PresentationBlock, ...],
) -> tuple[tuple[PresentationBlock, ...], bool]:
    """Append blocks when block_id is absent; never update existing entries."""
    if not new_blocks:
        return stored, False

    ordered_ids: list[str] = [block.block_id for block in stored]
    by_id: dict[str, PresentationBlock] = {block.block_id: block for block in stored}
    changed = False

    for block in new_blocks:
        if block.block_id in by_id:
            continue
        by_id[block.block_id] = block
        ordered_ids.append(block.block_id)
        changed = True

    if not changed:
        return stored, False

    merged = tuple(by_id[block_id] for block_id in ordered_ids if block_id in by_id)
    return merged, serialize_transcript_blocks(stored) != serialize_transcript_blocks(merged)


def merge_guidance_into_transcript(
    stored: tuple[PresentationBlock, ...],
    candidates: tuple[PresentationBlock, ...],
    *,
    frozen: bool,
) -> tuple[tuple[PresentationBlock, ...], bool]:
    """Idempotently merge guidance narration blocks into stored transcript."""
    if not candidates and stored:
        return stored, False

    ordered_ids: list[str] = [block.block_id for block in stored]
    by_id: dict[str, PresentationBlock] = {block.block_id: block for block in stored}

    for candidate in candidates:
        if candidate.block_id in by_id:
            existing = by_id[candidate.block_id]
            if frozen:
                continue
            if existing.to_dict() != candidate.to_dict():
                by_id[candidate.block_id] = candidate
            continue
        by_id[candidate.block_id] = candidate
        ordered_ids.append(candidate.block_id)

    merged = tuple(by_id[block_id] for block_id in ordered_ids if block_id in by_id)
    changed = serialize_transcript_blocks(stored) != serialize_transcript_blocks(merged)
    return merged, changed


def save_flow_guidance_transcript(task: Task, blocks: tuple[PresentationBlock, ...]) -> None:
    """Persist presentation transcript on task.outputs (not engineering truth)."""
    task.outputs[FLOW_GUIDANCE_TRANSCRIPT_KEY] = [block.to_dict() for block in blocks]


def transcript_is_frozen(task: Task) -> bool:
    return task.status == TaskStatus.COMPLETED
