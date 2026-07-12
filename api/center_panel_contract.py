"""Shared center-panel / report-preview presentation contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.display_role import (
    DISPLAY_ROLE_ORDER,
    DisplayRole,
    infer_display_fields_from_block,
    report_role_index,
    resolve_display_block,
    sort_blocks_by_report_role,
)

def _resolve_contract_path() -> Path:
    return Path(__file__).resolve().parents[1] / "contracts" / "center_panel_report_role_order.json"


_CONTRACT_PATH = _resolve_contract_path()


def load_report_role_order() -> tuple[str, ...]:
    payload = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("center_panel_report_role_order.json must be a JSON array")
    return tuple(str(item) for item in payload)


REPORT_ROLE_ORDER: tuple[str, ...] = load_report_role_order()


def infer_block_display_role(block: dict[str, Any]) -> str:
    resolved = resolve_display_block(block)
    return str(resolved.get("display_role") or "")


def normalize_scroll_block(block: dict[str, Any]) -> dict[str, Any]:
    """Normalize transcript or display output dicts to a shared scroll shape."""
    block_id = str(block.get("block_id") or block.get("id") or "").strip()
    normalized = resolve_display_block(block)
    normalized["id"] = block_id
    return normalized


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


def dedupe_blocks_by_id_inplace(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the last block for each id (update-in-place semantics)."""
    winners: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for block in blocks:
        block_id = str(block.get("id") or block.get("block_id") or "").strip()
        if not block_id:
            continue
        if block_id not in winners:
            order.append(block_id)
        winners[block_id] = block
    return [winners[block_id] for block_id in order if block_id in winners]


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
        elif kind == "text" and source in {"runtime", "workflow_node"}:
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
        elif kind == "next_workflows" and source == "workflow_runtime":
            scroll_blocks.append(
                normalize_scroll_block(
                    {
                        "id": raw.get("block_id"),
                        "type": "next_workflows",
                        "content": raw.get("text"),
                        "title": raw.get("title"),
                        "suggestions": raw.get("suggestions") or [],
                        "display_role": DisplayRole.next_workflows.value,
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
    guidance_blocks = [
        block
        for block in transcript_blocks_to_scroll_blocks(transcript_blocks)
        if str(block.get("display_role") or "") not in {
            DisplayRole.ask_archive.value,
            DisplayRole.answer_archive.value,
        }
    ]
    workflow_intro = [
        block
        for block in guidance_blocks
        if str(block.get("display_role") or "") == DisplayRole.workflow_intro.value
    ]
    narration = [
        block
        for block in guidance_blocks
        if str(block.get("display_role") or "") != DisplayRole.workflow_intro.value
    ]
    engineering_blocks = [
        normalize_scroll_block(block)
        for block in display_outputs
        if isinstance(block, dict) and str(block.get("id") or "") not in transcript_ids
    ]
    merged = dedupe_blocks_by_id([*workflow_intro, *engineering_blocks, *narration])
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
