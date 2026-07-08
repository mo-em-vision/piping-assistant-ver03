"""Shared center-panel / report-preview presentation contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1] / "contracts" / "center_panel_report_role_order.json"
)


def load_report_role_order() -> tuple[str, ...]:
    payload = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("center_panel_report_role_order.json must be a JSON array")
    return tuple(str(item) for item in payload)


REPORT_ROLE_ORDER: tuple[str, ...] = load_report_role_order()


def report_role_index(display_role: str | None) -> int:
    role = str(display_role or "").strip()
    if not role:
        return len(REPORT_ROLE_ORDER)
    try:
        return REPORT_ROLE_ORDER.index(role)
    except ValueError:
        return len(REPORT_ROLE_ORDER)


def infer_block_display_role(block: dict[str, Any]) -> str:
    role = str(block.get("display_role") or "").strip()
    if role:
        return role
    payload = block.get("payload")
    if isinstance(payload, dict):
        payload_role = str(payload.get("display_role") or "").strip()
        if payload_role:
            return payload_role
    block_id = str(block.get("block_id") or block.get("id") or "")
    if block_id.startswith("workflow-intro-"):
        return "workflow_intro"
    if block_id.startswith("result-summary-"):
        return "result_summary"
    if block_id.startswith("archived-ask-"):
        return "ask_archive"
    if block_id.startswith("archived-answer-"):
        return "answer_archive"
    if block_id.startswith("next-workflows-"):
        return "next_workflows"
    if block_id.startswith("guidance-"):
        return "branch_narration"
    if block_id.startswith("equation-trace-"):
        return "calculation_trace"
    if block_id.startswith("path-preview-equation-"):
        return "equation_preview"
    lifecycle = str(block.get("lifecycle") or "").strip()
    if lifecycle == "preview":
        return "equation_preview"
    return ""


def normalize_scroll_block(block: dict[str, Any]) -> dict[str, Any]:
    """Normalize transcript or display output dicts to a shared scroll shape."""
    block_id = str(block.get("block_id") or block.get("id") or "").strip()
    normalized = dict(block)
    normalized["id"] = block_id
    normalized["display_role"] = infer_block_display_role(block)
    return normalized


def sort_blocks_by_report_role(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [
        (index, report_role_index(str(block.get("display_role") or "")), block)
        for index, block in enumerate(blocks)
    ]
    indexed.sort(key=lambda item: (item[1], item[0]))
    return [block for _, _, block in indexed]


def dedupe_blocks_by_id(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    ordered: list[dict[str, Any]] = []
    for block in blocks:
        block_id = str(block.get("id") or block.get("block_id") or "").strip()
        if not block_id or block_id in seen:
            continue
        seen.add(block_id)
        ordered.append(block)
    return ordered


def transcript_blocks_to_scroll_blocks(transcript_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scroll_blocks: list[dict[str, Any]] = []
    for raw in transcript_blocks:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "")
        source = str(raw.get("source") or "")
        if kind == "guidance" and source == "guidance":
            scroll_blocks.append(
                normalize_scroll_block(
                    {
                        "id": raw.get("block_id"),
                        "type": "text",
                        "content": raw.get("text"),
                        "display_role": infer_block_display_role(raw),
                    }
                )
            )
        elif kind == "text" and source == "runtime":
            scroll_blocks.append(
                normalize_scroll_block(
                    {
                        "id": raw.get("block_id"),
                        "type": "text",
                        "content": raw.get("text"),
                        "display_role": infer_block_display_role(raw),
                    }
                )
            )
        elif source == "input_archive" and kind in {"ask_archive", "answer_archive"}:
            scroll_blocks.append(
                normalize_scroll_block(
                    {
                        "id": raw.get("block_id"),
                        "type": "text",
                        "content": raw.get("text"),
                        "display_role": kind,
                    }
                )
            )
        elif kind == "next_workflows" and source == "workflow_runtime":
            scroll_blocks.append(
                normalize_scroll_block(
                    {
                        "id": raw.get("block_id"),
                        "type": "next_workflows",
                        "content": raw.get("text"),
                        "title": raw.get("title"),
                        "suggestions": raw.get("suggestions") or [],
                        "display_role": "next_workflows",
                    }
                )
            )
    return scroll_blocks


def assemble_center_panel_scroll_blocks(
    *,
    transcript_blocks: list[dict[str, Any]],
    display_outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Assemble scroll blocks from transcript history + engineering snapshot."""
    transcript_ids = {
        str(block.get("block_id") or "").strip()
        for block in transcript_blocks
        if isinstance(block, dict) and block.get("block_id")
    }
    guidance_blocks = transcript_blocks_to_scroll_blocks(transcript_blocks)
    engineering_blocks = [
        normalize_scroll_block(block)
        for block in display_outputs
        if isinstance(block, dict) and str(block.get("id") or "") not in transcript_ids
    ]
    merged = dedupe_blocks_by_id([*guidance_blocks, *engineering_blocks])
    return sort_blocks_by_report_role(merged)


def presentation_package_from_task_state(state: dict[str, Any]) -> dict[str, Any]:
    """Presentation package shared by center panel scroll and report preview adapters."""
    transcript_blocks = [
        block
        for block in (state.get("flow_guidance") or {}).get("transcript_blocks") or []
        if isinstance(block, dict)
    ]
    display_outputs = [
        block for block in state.get("display_outputs") or [] if isinstance(block, dict)
    ]
    ordered_scroll_blocks = assemble_center_panel_scroll_blocks(
        transcript_blocks=transcript_blocks,
        display_outputs=display_outputs,
    )
    return {
        "transcript_blocks": transcript_blocks,
        "display_outputs": display_outputs,
        "ordered_scroll_blocks": ordered_scroll_blocks,
        "report_role_order": list(REPORT_ROLE_ORDER),
    }


def collect_visible_text(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in blocks:
        for key in ("content", "text", "title"):
            value = block.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
    return " ".join(parts)
