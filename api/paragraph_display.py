"""Generic paragraph/text display blocks for the center panel."""

from __future__ import annotations

from typing import Any

from api.display_block_metadata import (
    DISPLAY_CHANNEL_CURRENT_NODE_INTRO,
    DISPLAY_ROLE_INTRO,
    tag_display_block,
)
from api.node_context import _first_body_paragraph, display_heading_for_node
from engine.reference.paragraph_hierarchy import paragraph_reference
from engine.reference.standards_reader import StandardsReader

DISPLAY_ROLE_ENGINEERING_REFERENCE = "engineering_reference"


def _presentation_meta(metadata: dict[str, Any]) -> dict[str, Any]:
    raw = metadata.get("presentation")
    return raw if isinstance(raw, dict) else {}


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
    return node_id


def _reference_label(metadata: dict[str, Any], node_id: str) -> str:
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


def _summary_text(metadata: dict[str, Any], body: str) -> str:
    presentation = _presentation_meta(metadata)
    summary = str(presentation.get("summary") or "").strip()
    if summary:
        return summary
    excerpt = _first_body_paragraph(body)
    if excerpt:
        return excerpt
    text_block = metadata.get("text")
    if isinstance(text_block, dict):
        original = str(text_block.get("original") or "").strip()
        if original:
            collapsed = " ".join(original.split())
            return collapsed[:500] + ("…" if len(collapsed) > 500 else "")
    return ""


def build_paragraph_display_block(
    reader: StandardsReader,
    node_id: str,
    *,
    display_role: str = DISPLAY_ROLE_ENGINEERING_REFERENCE,
    block_id: str | None = None,
    content_suffix: str | None = None,
    display_channel: str | None = None,
    require_summary: bool = False,
) -> dict[str, Any] | None:
    """Build a durable or preview paragraph block from node presentation metadata."""
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

    presentation = _presentation_meta(metadata)
    summary = str(presentation.get("summary") or "").strip()
    if require_summary and not summary:
        body_summary = _first_body_paragraph(record.body)
        if not body_summary:
            return None

    content = _summary_text(metadata, record.body)
    if not content:
        return None

    if content_suffix:
        content = f"{content.rstrip('.')}{content_suffix}"

    ref_label = _reference_label(metadata, node_id)
    paragraph = paragraph_reference(metadata)
    resolved_block_id = block_id or f"paragraph-{node_id}"

    block: dict[str, Any] = {
        "id": resolved_block_id,
        "type": "text",
        "title": _paragraph_label(metadata, node_id) if display_role != DISPLAY_ROLE_INTRO else None,
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
    if display_role == DISPLAY_ROLE_INTRO:
        block["reference_links_placement"] = "inline"
        block["content_suffix"] = content_suffix

    channel = display_channel
    if display_role == DISPLAY_ROLE_INTRO and channel is None:
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
        block = build_paragraph_display_block(
            reader,
            node_id,
            require_summary=False,
        )
        if block is not None:
            blocks.append(block)

    return blocks
