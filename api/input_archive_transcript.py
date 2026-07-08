"""Submit-time durable ask/answer archive blocks for flow_guidance transcript."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.messaging.input_archive_display import (
    format_archive_answer_text,
    format_archive_ask_text,
)
from engine.reference.parameter_keys import canonical_parameter_key
from models.fact import Fact
from models.presentation import PresentationBlock
from models.task import Task

from api.flow_guidance_transcript import (
    archive_answer_block_id,
    archive_ask_block_id,
    load_flow_guidance_transcript_blocks,
    merge_append_only_blocks,
    save_flow_guidance_transcript,
)


@dataclass(frozen=True)
class InputArchiveEvent:
    """Captured submit context for one successful input archive append."""

    pre_submit_current_ask: dict[str, Any] | None
    submitted_parameter_id: str
    submitted_raw_value: Any
    submitted_unit: str | None
    fact: Fact


_MATERIAL_PARAMETER_ALIASES = frozenset({"material", "material_grade"})


def _parameter_ids_match(left: str, right: str) -> bool:
    left_key = canonical_parameter_key(left)
    right_key = canonical_parameter_key(right)
    if left_key == right_key:
        return True
    return left_key in _MATERIAL_PARAMETER_ALIASES and right_key in _MATERIAL_PARAMETER_ALIASES


def _ask_matches_submit(
    pre_submit_ask: dict[str, Any] | None,
    submitted_parameter_id: str,
) -> bool:
    if not isinstance(pre_submit_ask, dict):
        return False

    kind = str(pre_submit_ask.get("kind") or "")
    if kind not in {"input", "clarify"}:
        return False

    if kind == "clarify":
        return True

    ask_parameter = pre_submit_ask.get("parameter_id")
    if not isinstance(ask_parameter, str) or not ask_parameter.strip():
        return False

    return _parameter_ids_match(ask_parameter.strip(), submitted_parameter_id)


def build_input_archive_blocks(event: InputArchiveEvent) -> tuple[PresentationBlock, PresentationBlock] | None:
    """Build ask/answer archive blocks for one successful submit."""
    canonical_param = canonical_parameter_key(event.submitted_parameter_id)
    if not _ask_matches_submit(event.pre_submit_current_ask, canonical_param):
        return None

    ask_text = format_archive_ask_text(event.pre_submit_current_ask)
    if not ask_text:
        return None

    submission_id = str(event.fact.id).strip()
    if not submission_id:
        return None

    answer_text, answer_unit = format_archive_answer_text(event.fact, parameter_id=canonical_param)
    if not answer_text.strip():
        return None

    ask_block_id = archive_ask_block_id(canonical_param, submission_id)
    answer_block_id = archive_answer_block_id(canonical_param, submission_id)

    ask_block = PresentationBlock(
        block_id=ask_block_id,
        kind="ask_archive",
        source="input_archive",
        text=ask_text,
        payload={
            "display_role": "ask_archive",
            "parameter_id": canonical_param,
            "submission_id": submission_id,
        },
    )
    answer_payload: dict[str, Any] = {
        "display_role": "answer_archive",
        "parameter_id": canonical_param,
        "submission_id": submission_id,
        "submitted_display_value": answer_text,
        "fact_id": submission_id,
    }
    if answer_unit:
        answer_payload["unit"] = answer_unit

    answer_block = PresentationBlock(
        block_id=answer_block_id,
        kind="answer_archive",
        source="input_archive",
        text=answer_text,
        payload=answer_payload,
    )
    return ask_block, answer_block


def append_input_archive_transcript(task: Task, event: InputArchiveEvent) -> tuple[Task, bool]:
    """Append ask/answer archive blocks to task presentation transcript."""
    blocks = build_input_archive_blocks(event)
    if blocks is None:
        return task, False

    stored = load_flow_guidance_transcript_blocks(task)
    merged, changed = merge_append_only_blocks(stored, blocks)
    if not changed:
        return task, False

    save_flow_guidance_transcript(task, merged)
    return task, True
