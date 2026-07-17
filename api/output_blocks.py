"""Build ordered display output blocks for the desktop UI."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from api.center_panel_block_registry import canonicalize_center_panel_block_type
from api.center_panel_contract import dedupe_blocks_by_id_inplace
from api.display_block_metadata import (
    dedupe_blocks_by_id_prefer_richer,
    dedupe_competing_equation_preview_blocks,
    dedupe_equation_blocks_by_node_id,
    is_stable_equation_display_block_id,
    tag_display_block,
)
from models.display_role import DisplayRole, resolve_display_block, sort_blocks_by_report_role
from api.equation_evaluation_display import equation_display_blocks_for_task
from api.node_display import build_activated_node_blocks
from api.node_provenance import definition_node_id_for_task, enrich_display_blocks_provenance
from api.paragraph_display import paragraph_context_blocks_for_focus
from api.reference_links import enrich_display_output_dict, enrich_row_provenance_dict
from api.result_summary_display import build_result_summary_display_block
from api.workflow_bootstrap import resolve_activated_definition_node
from engine.reference.formula_display import load_equation_context
from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import planning_projection
from models.task import Task


def build_display_outputs(
    task: Task,
    *,
    standards_root: Path | None = None,
    reader: StandardsReader | None = None,
) -> list[dict[str, Any]]:
    planning = planning_projection(task)
    resolved_reader = reader or _reader_for(standards_root)
    trace = task.outputs.get("_execution_trace")
    has_trace = isinstance(trace, list) and bool(trace)
    trace_list = trace if has_trace else None

    blocks: list[dict[str, Any]] = []

    blocks.extend(_warning_blocks_from_task(task))
    blocks.extend(_workflow_scope_blocks(task, planning, resolved_reader))
    blocks.extend(_paragraph_context_blocks(task, planning, resolved_reader, trace=trace_list))
    blocks.extend(_equation_display_blocks(task, planning, resolved_reader, trace=trace_list))

    summary = build_result_summary_display_block(task, resolved_reader)
    if summary is not None:
        blocks.append(summary)

    return _finalize_display_blocks(blocks, resolved_reader, task=task, planning=planning)


def _finalize_display_blocks(
    blocks: list[dict[str, Any]],
    reader: StandardsReader,
    *,
    task: Task | None = None,
    planning: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    default_node_id = None
    if task is not None:
        default_node_id = definition_node_id_for_task(task, reader, planning)

    enrich_display_blocks_provenance(blocks, reader, default_node_id=default_node_id)
    _enrich_reference_links(blocks, reader, task=task)
    blocks = _strip_legacy_equation_blocks(blocks)
    blocks = dedupe_equation_blocks_by_node_id(blocks)
    blocks = dedupe_competing_equation_preview_blocks(blocks)
    blocks = dedupe_blocks_by_id_prefer_richer(blocks)
    blocks = dedupe_blocks_by_id_inplace(blocks)

    resolved: list[dict[str, Any]] = []
    for block in blocks:
        resolved.append(
            canonicalize_center_panel_block_type(resolve_display_block(block))
        )

    return sort_blocks_by_report_role(resolved)


def _enrich_reference_links(
    blocks: list[dict[str, Any]],
    reader: StandardsReader,
    *,
    task: Task | None = None,
) -> None:
    for index, block in enumerate(blocks):
        input_table = block.get("input_table")
        if isinstance(input_table, dict) and isinstance(input_table.get("rows"), list):
            from engine.equation.input_table import finalize_equation_input_table_row

            rows = [
                finalize_equation_input_table_row(
                    enrich_row_provenance_dict(row, reader, task=task),
                )
                if isinstance(row, dict)
                else row
                for row in input_table["rows"]
            ]
            table_copy = dict(input_table)
            table_copy["rows"] = rows
            block = dict(block)
            block["input_table"] = table_copy
            blocks[index] = enrich_display_output_dict(block, reader, task=task)
            continue
        blocks[index] = enrich_display_output_dict(block, reader, task=task)


def _strip_legacy_equation_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stable_equation_ids = {
        str(block.get("id") or "")
        for block in blocks
        if is_stable_equation_display_block_id(str(block.get("id") or ""))
    }
    filtered: list[dict[str, Any]] = []
    for block in blocks:
        block_id = str(block.get("id") or "")
        if block.get("type") == "equation" and not is_stable_equation_display_block_id(block_id):
            equation_node_id = str(block.get("equation_node_id") or "").strip()
            if equation_node_id and f"equation-{equation_node_id}" in stable_equation_ids:
                continue
        if block_id.startswith("path-preview-equation-"):
            continue
        if block_id.startswith("equation-trace-"):
            continue
        if block_id.startswith("node-activation-equation-"):
            continue
        filtered.append(block)
    return filtered


def _reader_for(standards_root: Path | None) -> StandardsReader:
    if standards_root is not None:
        return StandardsReader(standards_root, standard="asme_b31.3")
    project_root = Path(__file__).resolve().parent.parent
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _warning_blocks_from_task(task: Task) -> list[dict[str, Any]]:
    return [_warning_block(message) for message in task.warnings]


def _equation_blocks_show_awaiting_input(blocks: list[dict[str, Any]]) -> bool:
    from api.equation_inputs_display import AWAITING_USER_INPUT

    for block in blocks:
        if block.get("type") != "equation":
            continue
        table = block.get("input_table") or {}
        for row in table.get("rows") or []:
            if not isinstance(row, dict):
                continue
            if str(row.get("value") or "").strip() == AWAITING_USER_INPUT:
                return True
            provenance = row.get("value_provenance") or {}
            if isinstance(provenance, dict) and provenance.get("status") == "awaiting_user_input":
                return True
    return False


def _workflow_scope_blocks(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    return _activated_definition_blocks_for_focus(task, planning, reader)


def _paragraph_context_blocks(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
    *,
    trace: list[Any] | None,
) -> list[dict[str, Any]]:
    return paragraph_context_blocks_for_focus(task, planning, reader, trace=trace)


def _equation_display_blocks(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
    *,
    trace: list[Any] | None,
) -> list[dict[str, Any]]:
    paragraph_blocks = paragraph_context_blocks_for_focus(task, planning, reader, trace=trace)
    paragraph_ids = {
        str(block.get("source_node_id") or block.get("id", "").removeprefix("paragraph-"))
        for block in paragraph_blocks
    }
    activation_blocks = _activated_definition_blocks_for_focus(task, planning, reader)
    for block in activation_blocks:
        if block.get("type") == "equation":
            continue
    return equation_display_blocks_for_task(
        task,
        planning,
        reader,
        paragraph_node_ids=paragraph_ids,
    )


def _activated_definition_blocks(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    node_id = planning.get("active_definition_node")
    if not node_id:
        workflow_id = _task_workflow_id(task)
        if workflow_id:
            node_id = resolve_activated_definition_node(reader, workflow_id)
    if not node_id:
        for candidate in task.active_nodes:
            try:
                if str(reader.load(candidate).metadata.get("type", "")) == "definition":
                    node_id = candidate
                    break
            except FileNotFoundError:
                continue
    if not node_id:
        return []
    return build_activated_node_blocks(reader, str(node_id))


def _activated_definition_blocks_for_focus(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    """Activation blocks for the active calculation path only (no foreign-branch equations)."""
    from api.equation_evaluation_display import resolve_focus_node_for_equation_display

    focus_node = resolve_focus_node_for_equation_display(task, planning, reader)
    blocks = _activated_definition_blocks(task, planning, reader)
    if not focus_node:
        return [block for block in blocks if block.get("type") != "equation"]

    filtered: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") == "equation":
            continue
        filtered.append(block)
    return filtered


def _task_workflow_id(task: Task) -> str:
    workflow = task.outputs.get("workflow")
    return str(workflow) if workflow else ""


def _warning_block_id(message: str) -> str:
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()[:8]
    return f"warning-{digest}"


def _warning_block(message: str) -> dict[str, Any]:
    return tag_display_block(
        {
            "id": _warning_block_id(message),
            "type": "warning",
            "title": "Warning",
            "content": message,
            "variant": "warning",
        },
        display_role=DisplayRole.warning.value,
    )


def _format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
