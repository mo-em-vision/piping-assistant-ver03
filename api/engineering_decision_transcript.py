"""Persist engineering_decision blocks in flow_guidance transcript."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.flow_guidance_transcript import (
    load_flow_guidance_transcript_blocks,
    save_flow_guidance_transcript,
    serialize_transcript_blocks,
)
from api.node_provenance import provenance_for_node
from engine.messaging.decision_interaction_resolver import resolve_decision_interaction
from engine.messaging.decision_statement import render_decision_statement
from engine.reference.parameter_keys import canonical_parameter_key
from engine.reference.standards_reader import StandardsReader
from models.display_role import DisplayRole
from models.execution_context import Decision
from models.presentation import PresentationBlock
from models.task import Task


def engineering_decision_block_id(decision_key: str) -> str:
    return f"engineering-decision-{canonical_parameter_key(decision_key)}"


@dataclass(frozen=True)
class EngineeringDecisionEvent:
    decision_key: str
    decision: Decision


def merge_update_inplace_blocks(
    stored: tuple[PresentationBlock, ...],
    updated_blocks: tuple[PresentationBlock, ...],
) -> tuple[tuple[PresentationBlock, ...], bool]:
    """Merge blocks updating existing entries in place by block_id."""
    if not updated_blocks:
        return stored, False

    ordered_ids: list[str] = [block.block_id for block in stored]
    by_id: dict[str, PresentationBlock] = {block.block_id: block for block in stored}
    changed = False

    for block in updated_blocks:
        if block.block_id in by_id:
            if by_id[block.block_id].to_dict() != block.to_dict():
                by_id[block.block_id] = block
                changed = True
            continue
        by_id[block.block_id] = block
        ordered_ids.append(block.block_id)
        changed = True

    if not changed:
        return stored, False

    merged = tuple(by_id[block_id] for block_id in ordered_ids if block_id in by_id)
    return merged, serialize_transcript_blocks(stored) != serialize_transcript_blocks(merged)


def build_engineering_decision_block(
    reader: StandardsReader,
    task: Task,
    event: EngineeringDecisionEvent,
) -> PresentationBlock | None:
    decision_key = canonical_parameter_key(event.decision_key)
    view = resolve_decision_interaction(reader, task, decision_key)
    if view is None:
        return None

    activated_ids = list(event.decision.activated_node_ids or [])
    rendered_text = render_decision_statement(
        reader,
        view=view,
        selected_value=event.decision.selected_value,
        activated_node_ids=activated_ids,
    )

    requesting_node_id = event.decision.requesting_node_id or view.requesting_node_id
    provenance = provenance_for_node(reader, requesting_node_id, source_field="execution.interactions")
    payload: dict[str, Any] = {
        "display_role": DisplayRole.engineering_decision.value,
        "decision_key": decision_key,
        "interaction_id": event.decision.interaction_id or view.interaction_id,
        "requesting_node_id": requesting_node_id,
        "selected_value": str(event.decision.selected_value),
        "selected_label": event.decision.selected_label,
        "activated_node_ids": activated_ids,
        "rendered_text": rendered_text,
    }
    if provenance:
        payload["provenance"] = provenance

    return PresentationBlock(
        block_id=engineering_decision_block_id(decision_key),
        kind="text",
        source="engineering_decision",
        text=rendered_text,
        payload=payload,
    )


def append_engineering_decision_transcript(
    task: Task,
    reader: StandardsReader,
    event: EngineeringDecisionEvent,
) -> tuple[Task, bool]:
    block = build_engineering_decision_block(reader, task, event)
    if block is None:
        return task, False

    stored = load_flow_guidance_transcript_blocks(task)
    merged, changed = merge_update_inplace_blocks(stored, (block,))
    if not changed:
        return task, False

    save_flow_guidance_transcript(task, merged)
    return task, True


def latest_decision_for_key(task: Task, decision_key: str) -> Decision | None:
    canonical = canonical_parameter_key(decision_key)
    matches = [
        decision
        for decision in task.execution_context.decisions
        if canonical_parameter_key(decision.decision_key or decision.parameter) == canonical
    ]
    if not matches:
        return None
    return matches[-1]
