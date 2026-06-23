"""Build ordered display output blocks for the desktop UI."""

from __future__ import annotations

import re
from typing import Any

from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.task import Task, TaskStatus

_NODE_REFERENCES: dict[str, dict[str, str]] = {
    "B313-304.1.2": {
        "standard": "ASME B31.3",
        "paragraph": "304.1.2",
        "title": "Straight Pipe Under Internal Pressure",
        "excerpt": "The minimum required wall thickness for straight pipe under internal pressure shall be computed.",
    },
    "B313-material-stress": {
        "standard": "ASME B31.3",
        "paragraph": "Table A-1",
        "title": "Allowable Stress Lookup",
        "excerpt": "Allowable stress values are selected from Table A-1 for the design material and temperature.",
    },
    "B313-304.1.1": {
        "standard": "ASME B31.3",
        "paragraph": "304.1.1",
        "title": "Conditions for Internal Pressure",
        "excerpt": "Pressure design thickness and minimum required thickness relationships are defined in this section.",
    },
}

_RESULT_KEYS: tuple[tuple[str, str, str], ...] = (
    ("required_thickness", "Required Thickness", "mm"),
    ("t", "Required Thickness", "mm"),
    ("minimum_required_thickness", "Minimum Required Thickness", "mm"),
    ("t_m", "Minimum Required Thickness", "mm"),
    ("allowable_stress", "Allowable Stress", "MPa"),
    ("S", "Allowable Stress", "MPa"),
)

_WALL_THICKNESS_FORMULA = "t = PD / 2(SEW + PY)"


def build_display_outputs(task: Task) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    planning = task.outputs.get("planning_summary") or {}
    if not isinstance(planning, dict):
        planning = {}

    status_block = _planning_status_block(task, planning)
    if status_block:
        blocks.append(status_block)

    for warning in task.warnings:
        blocks.append(_warning_block(warning))

    blocks.extend(_result_blocks(task))

    trace = task.outputs.get("_execution_trace")
    if isinstance(trace, list) and trace:
        blocks.extend(_blocks_from_execution_trace(trace, task))
    elif _task_workflow_id(task) == PIPE_WALL_THICKNESS_DESIGN:
        blocks.extend(_preview_blocks_for_pipe_workflow(task, planning))

    return blocks


def _task_workflow_id(task: Task) -> str:
    workflow = task.outputs.get("workflow")
    return str(workflow) if workflow else ""


def _planning_status_block(task: Task, planning: dict[str, Any]) -> dict[str, Any] | None:
    action = planning.get("action")
    if not action and task.status != TaskStatus.AWAITING_INPUT:
        return None

    missing_inputs = planning.get("missing_inputs") or []
    missing_assumptions = planning.get("missing_assumptions") or []
    parts: list[str] = []

    goal = planning.get("goal")
    if goal:
        parts.append(f"Goal: {goal}.")

    if action == "request_input":
        if missing_inputs:
            parts.append(f"Waiting for inputs: {', '.join(str(item) for item in missing_inputs)}.")
        if missing_assumptions:
            parts.append(f"Waiting for assumptions: {', '.join(str(item) for item in missing_assumptions)}.")
    elif action:
        parts.append(f"Planner action: {action}.")
    elif task.status == TaskStatus.COMPLETED:
        parts.append("Calculation workflow completed.")
    elif task.status == TaskStatus.AWAITING_INPUT:
        parts.append("Task is waiting for engineering inputs.")

    if not parts:
        return None

    return {
        "id": "planning-status",
        "type": "text",
        "title": "Task status",
        "content": " ".join(parts),
        "variant": "body",
    }


def _warning_block(message: str) -> dict[str, Any]:
    return {
        "id": f"warning-{abs(hash(message)) % 10_000}",
        "type": "text",
        "title": "Warning",
        "content": message,
        "variant": "warning",
    }


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


def _blocks_from_execution_trace(trace: list[Any], task: Task) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    for index, entry in enumerate(trace):
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id") or f"node-{index}")
        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        outputs = entry.get("outputs") if isinstance(entry.get("outputs"), dict) else {}

        reference = _NODE_REFERENCES.get(node_id)
        if reference:
            blocks.append(
                {
                    "id": f"reference-{node_id}",
                    "type": "reference",
                    "title": reference["title"],
                    "standard": reference["standard"],
                    "paragraph": reference.get("paragraph"),
                    "excerpt": reference.get("excerpt"),
                    "source_node": node_id,
                }
            )

        calculation = node_trace.get("calculation")
        if isinstance(calculation, dict):
            blocks.extend(_calculation_blocks(node_id, calculation, outputs))

        lookup = node_trace.get("lookup")
        if isinstance(lookup, dict):
            table_block = _lookup_table_block(node_id, lookup)
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
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    formula = str(calculation.get("formula_display") or _WALL_THICKNESS_FORMULA)
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


def _lookup_table_block(node_id: str, lookup: dict[str, Any]) -> dict[str, Any] | None:
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

    columns = [{"key": key, "label": key.replace("_", " ").title(), "sortable": True} for key in normalized_rows[0]]
    return {
        "id": f"table-lookup-{node_id}",
        "type": "table",
        "title": "Lookup results",
        "columns": columns,
        "rows": normalized_rows,
        "searchable": True,
    }


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


def _preview_blocks_for_pipe_workflow(task: Task, planning: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    if task.outputs.get("required_thickness") is None and task.outputs.get("t") is None:
        blocks.append(
            {
                "id": "preview-equation",
                "type": "equation",
                "title": "Governing equation",
                "content": _display_to_latex(_WALL_THICKNESS_FORMULA),
                "display": _WALL_THICKNESS_FORMULA,
                "variables": [
                    {"symbol": "P", "name": "Design pressure"},
                    {"symbol": "D", "name": "Outside diameter"},
                    {"symbol": "S", "name": "Allowable stress"},
                    {"symbol": "E", "name": "Joint efficiency"},
                    {"symbol": "W", "name": "Weld strength reduction"},
                    {"symbol": "Y", "name": "Temperature coefficient"},
                ],
            }
        )

        missing = list(planning.get("missing_inputs") or [])
        if missing:
            blocks.append(
                {
                    "id": "preview-inputs-table",
                    "type": "table",
                    "title": "Inputs still required",
                    "columns": [
                        {"key": "parameter", "label": "Parameter", "sortable": True},
                        {"key": "status", "label": "Status", "sortable": True},
                    ],
                    "rows": [{"parameter": item, "status": "pending"} for item in missing],
                    "searchable": True,
                }
            )

        blocks.append(
            {
                "id": "preview-reference",
                "type": "reference",
                "title": "Straight Pipe Under Internal Pressure",
                "standard": "ASME B31.3",
                "paragraph": "304.1.2",
                "excerpt": _NODE_REFERENCES["B313-304.1.2"]["excerpt"],
                "source_node": "B313-304.1.2",
            }
        )

    return blocks


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
        text = f"{value:.6g}"
        return text
    return str(value)


def _display_to_latex(display: str) -> str:
    text = display.strip()
    if " = " in text and " / " in text:
        left, right = text.split(" = ", 1)
        numerator, denominator = right.split(" / ", 1)
        return f"{left.strip()} = \\frac{{{numerator.strip()}}}{{{denominator.strip()}}}"
    return re.sub(r"\s+", " ", text)
