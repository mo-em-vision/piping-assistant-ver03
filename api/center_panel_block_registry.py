"""Registry of canonical center-panel output block types."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1] / "contracts" / "center_panel_output_block_types.json"
)


def load_center_panel_block_registry() -> dict[str, Any]:
    payload = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("center_panel_output_block_types.json must be a JSON object")
    block_types = payload.get("block_types")
    if not isinstance(block_types, list) or not block_types:
        raise ValueError("center_panel_output_block_types.json must define block_types[]")
    return payload


def center_panel_block_type_entries() -> tuple[dict[str, Any], ...]:
    entries = load_center_panel_block_registry().get("block_types") or []
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("each block_types entry must be an object")
        block_type = str(entry.get("type") or "").strip()
        if not block_type:
            raise ValueError("each block_types entry requires type")
        normalized.append(dict(entry))
    return tuple(normalized)


def center_panel_block_types() -> frozenset[str]:
    return frozenset(str(entry["type"]) for entry in center_panel_block_type_entries())


def center_panel_block_desktop_components() -> dict[str, str]:
    return {
        str(entry["type"]): str(entry.get("desktop_component") or "").strip()
        for entry in center_panel_block_type_entries()
    }


_TEXT_DISPLAY_ROLE_TO_BLOCK_TYPE: dict[str, str] = {
    "warning": "warning",
    "paragraph_context": "paragraph_context",
    "result_summary": "result_summary",
    "applicability": "applicability",
}


def canonicalize_center_panel_block_type(block: Mapping[str, Any]) -> dict[str, Any]:
    """Map legacy ``type: text`` blocks to dedicated scroll block types by display_role."""
    resolved = dict(block)
    block_type = str(resolved.get("type") or "").strip()
    if block_type and block_type != "text":
        return resolved

    if not str(resolved.get("display_role") or "").strip():
        from models.display_role import infer_display_fields_from_block

        resolved = infer_display_fields_from_block(resolved)

    role = str(resolved.get("display_role") or "").strip()
    mapped = _TEXT_DISPLAY_ROLE_TO_BLOCK_TYPE.get(role)
    if mapped:
        resolved["type"] = mapped
    elif block_type:
        resolved["type"] = block_type
    else:
        resolved["type"] = "text"
    return resolved


def filter_center_panel_blocks(
    blocks: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> list[dict[str, Any]]:
    """Return registry-listed blocks with canonical block ``type`` values."""
    allowed = center_panel_block_types()
    filtered: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, Mapping):
            continue
        resolved = canonicalize_center_panel_block_type(block)
        block_type = str(resolved.get("type") or "").strip()
        if block_type in allowed:
            filtered.append(resolved)
    return filtered


def assert_blocks_use_registered_center_panel_types(
    blocks: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    *,
    context: str,
) -> None:
    allowed = center_panel_block_types()
    for index, block in enumerate(blocks):
        if not isinstance(block, Mapping):
            pytest.fail(f"{context}: block at index {index} is not a mapping")
        block_type = str(block.get("type") or "").strip()
        if not block_type:
            pytest.fail(f"{context}: block at index {index} is missing type")
        if block_type not in allowed:
            pytest.fail(
                f"{context}: unregistered center-panel block type {block_type!r} "
                f"(allowed: {sorted(allowed)})"
            )
