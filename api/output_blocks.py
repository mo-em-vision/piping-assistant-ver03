"""Build ordered display output blocks for the desktop UI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from api.center_panel_contract import dedupe_blocks_by_id_inplace
from api.display_block_metadata import (
    dedupe_blocks_by_id_prefer_richer,
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
    blocks.extend(_validation_blocks_from_trace(trace_list, task))

    if has_trace:
        blocks.extend(_lookup_and_non_equation_trace_blocks(trace_list, task, resolved_reader))

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
    blocks = dedupe_blocks_by_id_prefer_richer(blocks)
    blocks = dedupe_blocks_by_id_inplace(blocks)

    resolved: list[dict[str, Any]] = []
    for block in blocks:
        resolved.append(resolve_display_block(block))

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
            rows = [
                enrich_row_provenance_dict(row, reader, task=task)
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


def _validation_blocks_from_trace(
    trace: list[Any] | None,
    task: Task,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    thin_wall = task.outputs.get("thin_wall")
    if thin_wall is None:
        return blocks

    has_calculation = False
    if isinstance(trace, list):
        for entry in trace:
            if not isinstance(entry, dict):
                continue
            node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
            if node_trace.get("calculation"):
                has_calculation = True
                break

    if not has_calculation:
        return blocks

    if bool(thin_wall):
        content = "Thin-wall design criterion is satisfied for the evaluated thickness."
    else:
        content = (
            "Thin-wall design criterion is not satisfied; "
            "thick-wall design assumptions may apply."
        )

    blocks.append(
        tag_display_block(
            {
                "id": "validation-thin-wall-criterion",
                "type": "text",
                "title": None,
                "content": content,
                "variant": "body",
            },
            display_role=DisplayRole.applicability.value,
        )
    )
    return blocks


def _lookup_and_non_equation_trace_blocks(
    trace: list[Any],
    task: Task,
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    for index, entry in enumerate(trace):
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id") or f"node-{index}")
        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}

        calculation = node_trace.get("calculation")
        if isinstance(calculation, dict):
            blocks.extend(_non_equation_calculation_blocks(node_id, calculation))

        lookup = node_trace.get("lookup")
        if isinstance(lookup, dict):
            table_block = _lookup_table_block(node_id, lookup, reader=reader)
            if table_block:
                blocks.append(table_block)

    graph_block = _intermediate_graph_block(trace)
    if graph_block:
        blocks.append(graph_block)

    return blocks


def _non_equation_calculation_blocks(
    node_id: str,
    calculation: dict[str, Any],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    steps = calculation.get("steps")
    if isinstance(steps, list) and steps:
        rows: list[dict[str, Any]] = []
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            result = step.get("result")
            rows.append(
                {
                    "step": step.get("name") or f"Step {step_index + 1}",
                    "description": step.get("description") or "",
                    "result": _format_step_result(result),
                }
            )
        if rows:
            blocks.append(
                {
                    "id": f"table-steps-{node_id}",
                    "type": "table",
                    "title": "Calculation steps",
                    "columns": [
                        {"key": "step", "label": "Step", "sortable": True},
                        {"key": "description", "label": "Description", "sortable": True},
                        {"key": "result", "label": "Result", "sortable": False},
                    ],
                    "rows": rows,
                    "searchable": True,
                }
            )

    intermediates = calculation.get("intermediate_values")
    if isinstance(intermediates, dict) and intermediates:
        rows = [
            {"symbol": key, "value": _format_number(value)}
            for key, value in intermediates.items()
            if isinstance(value, (int, float))
        ]
        if rows:
            blocks.append(
                {
                    "id": f"table-intermediates-{node_id}",
                    "type": "table",
                    "title": "Intermediate values",
                    "columns": [
                        {"key": "symbol", "label": "Symbol", "sortable": True},
                        {"key": "value", "label": "Value", "sortable": True},
                    ],
                    "rows": rows,
                    "searchable": False,
                }
            )

    return blocks


def _task_workflow_id(task: Task) -> str:
    workflow = task.outputs.get("workflow")
    return str(workflow) if workflow else ""


def _warning_block(message: str) -> dict[str, Any]:
    return tag_display_block(
        {
            "id": f"warning-{abs(hash(message)) % 10_000}",
            "type": "text",
            "title": "Warning",
            "content": message,
            "variant": "warning",
        },
        display_role=DisplayRole.warning.value,
    )


def _lookup_table_block(
    node_id: str,
    lookup: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any] | None:
    rows = lookup.get("rows") or lookup.get("matches")
    if not isinstance(rows, list) or not rows:
        return None

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized_rows.append({str(key): value for key, value in row.items()})
        else:
            normalized_rows.append({"value": row})

    if not normalized_rows:
        return None

    columns = [
        {"key": key, "label": key.replace("_", " ").title(), "sortable": True}
        for key in normalized_rows[0]
    ]

    table_id = str(lookup.get("table_id") or node_id).strip()
    title = str(lookup.get("title") or "").strip()
    if not title and reader is not None:
        try:
            from api.node_context import display_heading_for_node

            title = display_heading_for_node(reader.load(table_id).metadata) or "Lookup results"
        except FileNotFoundError:
            title = "Lookup results"
    if not title:
        title = "Lookup results"

    highlight = lookup.get("highlight")
    recommendation_summary = str(lookup.get("recommendation_summary") or "").strip()
    display_role = (
        DisplayRole.lookup_table_recommendation.value
        if highlight
        else DisplayRole.engineering_reference.value
    )

    block: dict[str, Any] = {
        "id": f"table-lookup-{node_id}",
        "type": "table",
        "title": title,
        "columns": columns,
        "rows": normalized_rows,
        "searchable": True,
        "refs": {"table_id": table_id, "node_id": table_id},
    }
    if isinstance(highlight, dict) and highlight:
        block["highlight_row"] = highlight
    if recommendation_summary:
        block["summary_text"] = recommendation_summary

    return tag_display_block(block, display_role=display_role, source_node_id=node_id)


def _intermediate_graph_block(trace: list[Any]) -> dict[str, Any] | None:
    points: list[dict[str, Any]] = []

    for entry in trace:
        if not isinstance(entry, dict):
            continue
        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        intermediates = node_trace.get("intermediates")
        if isinstance(intermediates, dict):
            for key, value in intermediates.items():
                if isinstance(value, (int, float)):
                    points.append({"x": key, "y": float(value)})

        calculation = node_trace.get("calculation")
        if isinstance(calculation, dict):
            final = calculation.get("final_result")
            if isinstance(final, dict) and isinstance(final.get("value"), (int, float)):
                points.append({"x": "t", "y": float(final["value"])})

    if len(points) < 2:
        return None

    return {
        "id": "graph-intermediates",
        "type": "graph",
        "title": "Calculation terms",
        "chart_type": "bar",
        "x_label": "Term",
        "y_label": "SI value",
        "series": [{"name": "Values", "points": points}],
    }


def _format_step_result(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, dict):
        parts = [f"{key}={_format_number(value)}" for key, value in result.items()]
        return ", ".join(parts)
    return str(result)


def _format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
