"""Flow Guidance Layer — merge guidance, prompts, and assets into UI-neutral output."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from engine.messaging.formula_parameter_prompt import build_formula_parameter_prompt
from engine.messaging.step_prompt import build_step_prompt
from engine.reference.standards_reader import StandardsReader
from models.planning import NavigationPlan
from models.presentation import (
    GuidanceBlock,
    PresentationBlock,
    PresentationResponse,
    append_transcript_blocks,
    rebuild_presentation_snapshot,
)
from models.task import Task


def _guidance_to_presentation(block: GuidanceBlock) -> PresentationBlock:
    return PresentationBlock(
        block_id=block.block_id,
        kind=block.kind,
        source=block.source,
        text=block.text,
        refs=dict(block.refs),
    )


def _prompt_block(text: str, *, block_id: str | None = None) -> PresentationBlock:
    return PresentationBlock(
        block_id=block_id or f"prompt-{uuid4().hex[:8]}",
        kind="prompt",
        source="messaging",
        text=text.strip(),
    )


def _warning_blocks(warnings: tuple[str, ...]) -> tuple[PresentationBlock, ...]:
    return tuple(
        PresentationBlock(
            block_id=f"warning-{index}",
            kind="warning",
            source="validation",
            text=message.strip(),
        )
        for index, message in enumerate(warnings)
        if message.strip()
    )


def _resolve_deterministic_prompt(
    *,
    reader: StandardsReader,
    task: Task,
    navigation_plan: NavigationPlan | None,
    missing_input_ids: list[str] | None,
) -> str | None:
    if navigation_plan is None:
        return None

    prompt = build_step_prompt(
        reader=reader,
        task=task,
        navigation_plan=navigation_plan,
        missing_input_ids=missing_input_ids,
    )
    if prompt:
        return prompt

    return build_formula_parameter_prompt(
        reader=reader,
        task=task,
        navigation_plan=navigation_plan,
        missing_input_ids=missing_input_ids or [],
    )


class ResponseComposer:
    """Combine guidance blocks with deterministic messaging prompts and assets."""

    def compose(
        self,
        *,
        task: Task,
        reader: StandardsReader,
        guidance_blocks: tuple[GuidanceBlock, ...] = (),
        transcript_blocks: tuple[PresentationBlock, ...] = (),
        planning: dict[str, Any] | None = None,
        navigation_plan: NavigationPlan | None = None,
        missing_input_ids: list[str] | None = None,
        validation_warnings: tuple[str, ...] = (),
    ) -> PresentationResponse:
        """Build UI-neutral presentation output for CLI and future API/Desktop consumers."""
        del planning  # reserved for API/desktop planning projection; navigation_plan is authoritative

        guidance_presentation = tuple(
            _guidance_to_presentation(block) for block in guidance_blocks
        )
        warning_presentation = _warning_blocks(validation_warnings)

        prompt_text = _resolve_deterministic_prompt(
            reader=reader,
            task=task,
            navigation_plan=navigation_plan,
            missing_input_ids=missing_input_ids,
        )
        active_prompt = _prompt_block(prompt_text) if prompt_text else None

        snapshot_parts: list[PresentationBlock] = [
            *guidance_presentation,
            *warning_presentation,
        ]
        if active_prompt is not None:
            snapshot_parts.append(active_prompt)

        presentation_blocks = rebuild_presentation_snapshot(tuple(snapshot_parts))

        return PresentationResponse(
            presentation_blocks=presentation_blocks,
            transcript_blocks=transcript_blocks,
            active_prompt=active_prompt,
        )


def presentation_blocks_for_transcript_append(
    *,
    prior_transcript: tuple[PresentationBlock, ...],
    response: PresentationResponse,
) -> tuple[PresentationBlock, ...]:
    """Return new blocks to append this turn without duplicating prior transcript ids."""
    prior_ids = {block.block_id for block in prior_transcript}
    new_blocks: list[PresentationBlock] = []
    for block in response.presentation_blocks:
        if block.block_id not in prior_ids:
            new_blocks.append(block)
    if (
        response.active_prompt is not None
        and response.active_prompt.block_id not in prior_ids
        and response.active_prompt not in new_blocks
    ):
        new_blocks.append(response.active_prompt)
    return tuple(new_blocks)


def append_presentation_to_transcript(
    prior_transcript: tuple[PresentationBlock, ...],
    response: PresentationResponse,
) -> tuple[PresentationBlock, ...]:
    """Append only new presentation blocks from this turn to transcript history."""
    return append_transcript_blocks(
        prior_transcript,
        presentation_blocks_for_transcript_append(
            prior_transcript=prior_transcript,
            response=response,
        ),
    )
