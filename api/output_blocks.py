"""Build ordered display output blocks for the desktop UI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from api.display_block_metadata import (
    DISPLAY_CHANNEL_CURRENT_NODE_INTRO,
    DISPLAY_ROLE_APPLICABILITY,
    DISPLAY_ROLE_RECOMMENDATION,
    DISPLAY_ROLE_WARNING,
    append_equation_trace_blocks,
    dedupe_competing_equation_preview_blocks,
    dedupe_preview_tier_equations,
    evaluated_equation_node_ids,
    tag_display_block,
)
from api.equation_evaluation_display import (
    build_equation_evaluation_block,
    resolve_equation_node_for_display,
    resolve_focus_node_for_equation_display,
)
from api.node_display import build_activated_node_blocks
from api.node_provenance import definition_node_id_for_task, enrich_display_blocks_provenance
from api.paragraph_display import build_paragraph_display_block, paragraph_blocks_from_trace
from api.workflow_bootstrap import resolve_activated_definition_node
from engine.reference.formula_display import load_equation_context
from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import planning_projection
from models.task import Task, TaskStatus

_RESULT_KEYS: tuple[tuple[str, str, str], ...] = (
    ("required_thickness", "Required Thickness", "mm"),
    ("t", "Required Thickness", "mm"),
    ("minimum_required_thickness", "Minimum Required Pipe Wall Thickness", "mm"),
    ("t_m", "Minimum Required Pipe Wall Thickness", "mm"),
    ("mawp", "Maximum Allowable Working Pressure (MAWP)", "Pa"),
    ("MAWP", "Maximum Allowable Working Pressure (MAWP)", "Pa"),
)


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

    for warning in task.warnings:
        blocks.append(_warning_block(warning))

    blocks.extend(_activated_definition_blocks_for_focus(task, planning, resolved_reader))
    blocks.extend(_path_calculation_preview_blocks(task, planning, resolved_reader, trace=trace_list))
    blocks.extend(paragraph_blocks_from_trace(trace_list, resolved_reader))
    blocks.extend(_validation_blocks_from_trace(trace_list, task))

    if has_trace:
        blocks.extend(_blocks_from_execution_trace(trace_list, task, resolved_reader))

    blocks.extend(_result_blocks(task))

    return _finalize_display_blocks(blocks, resolved_reader, task=task, planning=planning)


def _dedupe_blocks_by_id(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for block in blocks:
        block_id = str(block.get("id") or "")
        if block_id and block_id in seen:
            continue
        if block_id:
            seen.add(block_id)
        deduped.append(block)
    return deduped


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
    blocks = dedupe_preview_tier_equations(blocks)
    blocks = dedupe_competing_equation_preview_blocks(blocks)
    if task is not None:
        blocks = append_equation_trace_blocks(blocks, task, reader)
    return _dedupe_blocks_by_id(blocks)


def _reader_for(standards_root: Path | None) -> StandardsReader:
    if standards_root is not None:
        return StandardsReader(standards_root, standard="asme_b31.3")
    project_root = Path(__file__).resolve().parent.parent
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


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
    focus_node = resolve_focus_node_for_equation_display(task, planning, reader)
    blocks = _activated_definition_blocks(task, planning, reader)
    if not focus_node:
        return blocks

    filtered: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") == "equation":
            source_node_id = str(block.get("source_node_id") or "")
            if source_node_id and source_node_id != str(focus_node):
                continue
        filtered.append(block)
    return filtered


def _path_calculation_preview_blocks(
    task: Task,
    planning: dict[str, Any],
    reader: StandardsReader,
    *,
    trace: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """After path expansion, preview the focus calculation node's governing equation."""
    void = trace
    selected_node = resolve_focus_node_for_equation_display(task, planning, reader)
    if not selected_node:
        return []

    equation_id = resolve_equation_node_for_display(reader, str(selected_node), task)
    evaluated_ids = evaluated_equation_node_ids(task)
    if equation_id and equation_id in evaluated_ids:
        return []

    blocks: list[dict[str, Any]] = []
    intro = build_paragraph_display_block(
        reader,
        str(selected_node),
        display_role="intro",
        block_id=f"path-preview-intro-{selected_node}",
        content_suffix=" with the following equation:",
        display_channel=DISPLAY_CHANNEL_CURRENT_NODE_INTRO,
    )
    if intro is not None:
        blocks.append(intro)

    equation_block = build_equation_evaluation_block(
        task,
        reader,
        str(selected_node),
    )
    if equation_block:
        block_eq_id = str(equation_block.get("equation_node_id") or equation_id or "")
        if block_eq_id and block_eq_id in evaluated_ids:
            return blocks
        blocks.append(equation_block)

    return blocks


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
            display_role=DISPLAY_ROLE_APPLICABILITY,
        )
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
        display_role=DISPLAY_ROLE_WARNING,
    )


def _result_blocks(task: Task) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    seen_labels: set[str] = set()

    for key, label, default_unit in _RESULT_KEYS:
        if key not in task.outputs or label in seen_labels:
            continue
        value = task.outputs[key]
        if value is None:
            continue
        seen_labels.add(label)
        unit = str(task.outputs.get(f"{key}_unit") or default_unit)
        status = "pass" if task.status == TaskStatus.COMPLETED else "info"
        blocks.append(
            {
                "id": f"result-{key}",
                "type": "result",
                "title": label,
                "label": label,
                "value": _format_number(value),
                "unit": unit,
                "status": status,
            }
        )

    return blocks


def _blocks_from_execution_trace(
    trace: list[Any],
    task: Task,
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    evaluated_ids = evaluated_equation_node_ids(task)

    for index, entry in enumerate(trace):
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id") or f"node-{index}")
        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        outputs = entry.get("outputs") if isinstance(entry.get("outputs"), dict) else {}

        calculation = node_trace.get("calculation")
        if isinstance(calculation, dict):
            equation_id = resolve_equation_node_for_display(reader, node_id, task)
            skip_equation = bool(equation_id and equation_id in evaluated_ids)
            blocks.extend(
                _calculation_blocks(
                    node_id,
                    calculation,
                    outputs,
                    reader=reader,
                    skip_equation=skip_equation,
                )
            )

        lookup = node_trace.get("lookup")
        if isinstance(lookup, dict):
            table_block = _lookup_table_block(node_id, lookup, reader=reader)
            if table_block:
                blocks.append(table_block)

    graph_block = _intermediate_graph_block(trace)
    if graph_block:
        blocks.append(graph_block)

    if task.status == TaskStatus.COMPLETED and not any(block["type"] == "result" for block in blocks):
        blocks.extend(_result_blocks(task))

    return blocks


def _calculation_blocks(
    node_id: str,
    calculation: dict[str, Any],
    outputs: dict[str, Any],
    *,
    reader: StandardsReader,
    skip_equation: bool = False,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    if not skip_equation:
        formula = str(calculation.get("formula_display") or "")
        if not formula:
            formula = _equation_formula_from_node(reader, node_id)
        if formula:
            variables = _variable_rows(calculation, outputs)
            blocks.append(
                {
                    "id": f"equation-{node_id}",
                    "type": "equation",
                    "title": "Governing equation",
                    "content": _display_to_latex(formula),
                    "display": formula,
                    "variables": variables,
                    "result": _equation_result(outputs),
                }
            )

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


def _equation_formula_from_node(reader: StandardsReader, node_id: str) -> str:
    try:
        ctx = load_equation_context(reader, node_id)
        if isinstance(ctx, dict):
            display = ctx.get("display")
            if isinstance(display, dict):
                text = display.get("text")
                if text:
                    return str(text)
            elif display:
                return str(display)
        elif getattr(ctx, "display", None):
            return str(ctx.display)
    except (FileNotFoundError, TypeError, ValueError):
        pass
    try:
        record = reader.load(node_id)
        metadata = record.metadata
        if str(metadata.get("type")) == "equation":
            latex = metadata.get("display_latex") or metadata.get("sympy")
            if latex:
                return str(latex)
    except FileNotFoundError:
        pass
    return ""


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
    display_role = DISPLAY_ROLE_RECOMMENDATION if highlight else "engineering_reference"

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


def _variable_rows(calculation: dict[str, Any], outputs: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    variables = calculation.get("variables")
    if isinstance(variables, dict):
        for symbol, payload in variables.items():
            if not isinstance(payload, dict):
                continue
            rows.append(
                {
                    "symbol": str(payload.get("symbol") or symbol),
                    "name": str(payload.get("description") or payload.get("name") or symbol),
                    "value": _format_number(payload.get("value")) if payload.get("value") is not None else None,
                    "unit": payload.get("unit"),
                }
            )

    if not rows and outputs:
        for key, value in outputs.items():
            if key in {"thin_wall"}:
                continue
            if isinstance(value, (int, float, str)):
                rows.append({"symbol": key, "name": key.replace("_", " ").title(), "value": _format_number(value)})

    return rows


def _equation_result(outputs: dict[str, Any]) -> dict[str, Any] | None:
    for key, label, unit in _RESULT_KEYS:
        if key in outputs and outputs[key] is not None:
            return {
                "label": label,
                "value": _format_number(outputs[key]),
                "unit": unit,
            }
    return None


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


def _display_to_latex(display: str) -> str:
    text = display.strip()
    if " = " in text and " / " in text:
        left, right = text.split(" = ", 1)
        numerator, denominator = right.split(" / ", 1)
        return f"{left.strip()} = \\frac{{{numerator.strip()}}}{{{denominator.strip()}}}"
    return re.sub(r"\s+", " ", text)
