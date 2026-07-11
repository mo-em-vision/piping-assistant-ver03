"""Generic paragraph/text display blocks for the center panel."""

from __future__ import annotations

from typing import Any

from api.display_block_metadata import (
    DISPLAY_CHANNEL_CURRENT_NODE_INTRO,
    tag_display_block,
)
from api.node_context import display_heading_for_node
from engine.reference.paragraph_hierarchy import paragraph_reference
from engine.reference.standards_reader import StandardsReader
from models.display_role import DisplayRole


def _presentation_meta(metadata: dict[str, Any]) -> dict[str, Any]:
    raw = metadata.get("presentation")
    return raw if isinstance(raw, dict) else {}


def presentation_summary(metadata: dict[str, Any]) -> str:
    """Return presentation.summary only; no fallback to node body or text.original."""
    return str(_presentation_meta(metadata).get("summary") or "").strip()


def _paragraph_label(metadata: dict[str, Any], node_id: str) -> str:
    presentation = _presentation_meta(metadata)
    display_label = str(presentation.get("display_label") or "").strip()
    if display_label:
        return display_label
    heading = display_heading_for_node(metadata)
    if heading:
        return heading
    paragraph = paragraph_reference(metadata)
    if paragraph:
        return f"§{paragraph}"
    return ""


def paragraph_reference_label(metadata: dict[str, Any], node_id: str) -> str:
    presentation = _presentation_meta(metadata)
    ref_label = str(presentation.get("reference_label") or "").strip()
    if ref_label:
        return ref_label
    paragraph = paragraph_reference(metadata)
    if paragraph:
        display = paragraph
        if display.endswith("-a") or display.endswith("-b"):
            import re

            display = re.sub(r"-[a-z]$", "", display)
        return f"§{display}"
    return _paragraph_label(metadata, node_id)


def build_equation_context_from_paragraph(
    reader: StandardsReader,
    node_id: str,
    *,
    context_lead: str = "with the following equation:",
) -> dict[str, str] | None:
    """Paragraph summary grouped with the equation preview/trace block."""
    node_id = str(node_id or "").strip()
    if not node_id:
        return None
    try:
        record = reader.load(node_id)
    except FileNotFoundError:
        return None

    summary = presentation_summary(record.metadata)
    if not summary:
        return None

    context: dict[str, str] = {"context_intro": summary}
    lead = str(context_lead or "").strip()
    if lead:
        context["context_lead"] = lead
    return context


def build_paragraph_display_block(
    reader: StandardsReader,
    node_id: str,
    *,
    display_role: str = DisplayRole.engineering_reference.value,
    block_id: str | None = None,
    content_suffix: str | None = None,
    display_channel: str | None = None,
) -> dict[str, Any] | None:
    """Build a durable paragraph block from presentation.summary only."""
    node_id = str(node_id or "").strip()
    if not node_id:
        return None

    try:
        record = reader.load(node_id)
    except FileNotFoundError:
        return None

    metadata = record.metadata
    node_type = str(metadata.get("type") or "").strip()
    if node_type not in {"paragraph", "definition", "text"}:
        return None

    content = presentation_summary(metadata)
    if not content:
        return None

    if content_suffix:
        content = f"{content.rstrip('.')}{content_suffix}"

    ref_label = paragraph_reference_label(metadata, node_id)
    paragraph = paragraph_reference(metadata)
    resolved_block_id = block_id or f"paragraph-{node_id}"

    block: dict[str, Any] = {
        "id": resolved_block_id,
        "type": "text",
        "title": (
            (_paragraph_label(metadata, node_id) or None)
            if display_role != DisplayRole.node_intro.value
            else None
        ),
        "content": content,
        "variant": "body",
        "reference_links": [
            {
                "node_id": node_id,
                "label": ref_label,
                "paragraph": paragraph or None,
            }
        ],
        "refs": {"node_id": node_id},
    }
    if display_role == DisplayRole.node_intro.value:
        block["reference_links_placement"] = "inline"
        block["content_suffix"] = content_suffix

    channel = display_channel
    if display_role == DisplayRole.node_intro.value and channel is None:
        channel = DISPLAY_CHANNEL_CURRENT_NODE_INTRO

    return tag_display_block(
        block,
        display_role=display_role,
        source_node_id=node_id,
        display_channel=channel,
    )


def paragraph_blocks_from_trace(
    trace: list[Any] | None,
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    """Emit paragraph blocks for paragraph nodes visited in the execution trace."""
    if not isinstance(trace, list):
        return []

    blocks: list[dict[str, Any]] = []
    seen: set[str] = set()

    for entry in trace:
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id") or "").strip()
        if not node_id or node_id in seen:
            continue
        try:
            node_type = str(reader.load(node_id).metadata.get("type") or "")
        except FileNotFoundError:
            continue
        if node_type != "paragraph":
            continue
        seen.add(node_id)
        block = build_paragraph_display_block(reader, node_id)
        if block is not None:
            blocks.append(block)

    return blocks


def _paragraph_node_ids_from_trace(
    trace: list[Any] | None,
    reader: StandardsReader,
) -> list[str]:
    if not isinstance(trace, list):
        return []
    node_ids: list[str] = []
    seen: set[str] = set()
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id") or "").strip()
        if not node_id or node_id in seen:
            continue
        try:
            node_type = str(reader.load(node_id).metadata.get("type") or "")
        except FileNotFoundError:
            continue
        if node_type != "paragraph":
            continue
        seen.add(node_id)
        node_ids.append(node_id)
    return node_ids


def paragraph_context_blocks_for_focus(
    task: Any,
    planning: dict[str, Any],
    reader: StandardsReader,
    *,
    trace: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Emit live paragraph_context blocks for focus and visited paragraph nodes."""
    from api.equation_evaluation_display import resolve_focus_node_for_equation_display

    node_ids: list[str] = []
    seen: set[str] = set()

    focus_node = resolve_focus_node_for_equation_display(task, planning, reader)
    if focus_node:
        try:
            if str(reader.load(focus_node).metadata.get("type") or "") == "paragraph":
                node_ids.append(focus_node)
                seen.add(focus_node)
        except FileNotFoundError:
            pass

    for node_id in _paragraph_node_ids_from_trace(trace, reader):
        if node_id not in seen:
            seen.add(node_id)
            node_ids.append(node_id)

    blocks: list[dict[str, Any]] = []
    for node_id in node_ids:
        block = build_paragraph_display_block(
            reader,
            node_id,
            display_role=DisplayRole.paragraph_context.value,
        )
        if block is not None:
            blocks.append(block)
    return blocks

