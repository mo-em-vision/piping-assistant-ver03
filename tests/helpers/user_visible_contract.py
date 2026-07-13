"""Guards for user-facing serialized table/text content."""

from __future__ import annotations

import json
from typing import Any, Iterator

import pytest

PLANNER_BLOB_MARKERS: tuple[str, ...] = (
    "engineering_plan",
    "legacy_goal_map",
    "waiting_user_input",
    "GOAL-",
    "REQ-",
    '"requirements"',
    '"root_goal"',
    '"traversal"',
)

_TABLE_ROW_STRING_KEYS: tuple[str, ...] = (
    "symbol",
    "definition",
    "parameter",
    "description",
    "value",
    "name",
    "label",
    "unit",
    "display_value",
    "source",
    "status",
    "field",
    "resolution_label",
    "resolution_kind",
    "display_status",
)


def is_planner_blob_text(text: str) -> bool:
    normalized = str(text or "").strip()
    if not normalized:
        return False
    if normalized.startswith("{") and '"GOAL-' in normalized:
        return True
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        keys = set(parsed)
        if keys & {"requirements", "root_goal", "traversal", "legacy_goal_map"}:
            return True
        if any(str(key).startswith("GOAL-") for key in parsed):
            return True
    lower = normalized.lower()
    return any(marker.lower() in lower for marker in PLANNER_BLOB_MARKERS)


def assert_user_visible_text(text: str, *, context: str = "") -> None:
    if is_planner_blob_text(text):
        prefix = f"{context}: " if context else ""
        pytest.fail(f"{prefix}planner blob leaked into user-facing content: {text!r}")


def _yield_string_fields(
    payload: dict[str, Any],
    *,
    prefix: str,
) -> Iterator[tuple[str, str]]:
    for key in _TABLE_ROW_STRING_KEYS:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            continue
        text = str(value).strip()
        if text:
            yield f"{prefix}.{key}", text


def iter_display_output_table_cells(state: dict[str, Any]) -> Iterator[tuple[str, str]]:
    for block in state.get("display_outputs") or []:
        if not isinstance(block, dict):
            continue
        block_id = str(block.get("id") or "display_output")
        input_table = block.get("input_table")
        if not isinstance(input_table, dict):
            continue
        for index, row in enumerate(input_table.get("rows") or []):
            if not isinstance(row, dict):
                continue
            yield from _yield_string_fields(row, prefix=f"display_outputs.{block_id}.rows[{index}]")


def iter_parameter_table_cells(state: dict[str, Any]) -> Iterator[tuple[str, str]]:
    for index, param in enumerate(state.get("parameters") or []):
        if not isinstance(param, dict):
            continue
        yield from _yield_string_fields(param, prefix=f"parameters[{index}]")


def iter_task_state_views_table_cells(views: dict[str, Any]) -> Iterator[tuple[str, str]]:
    for index, row in enumerate(views.get("facts_view") or []):
        if isinstance(row, dict):
            yield from _yield_string_fields(row, prefix=f"facts_view[{index}]")
    for index, row in enumerate(views.get("decisions_view") or []):
        if isinstance(row, dict):
            yield from _yield_string_fields(row, prefix=f"decisions_view[{index}]")
    for index, row in enumerate(views.get("outputs_view") or []):
        if isinstance(row, dict):
            yield from _yield_string_fields(row, prefix=f"outputs_view[{index}]")
    for index, row in enumerate(views.get("trace_timeline") or []):
        if isinstance(row, dict):
            yield from _yield_string_fields(row, prefix=f"trace_timeline[{index}]")


def assert_task_state_table_cells_exclude_planner_blobs(state: dict[str, Any]) -> None:
    for context, text in (
        *iter_display_output_table_cells(state),
        *iter_parameter_table_cells(state),
    ):
        assert_user_visible_text(text, context=context)


def assert_task_state_views_table_cells_exclude_planner_blobs(views: dict[str, Any]) -> None:
    for context, text in iter_task_state_views_table_cells(views):
        assert_user_visible_text(text, context=context)
