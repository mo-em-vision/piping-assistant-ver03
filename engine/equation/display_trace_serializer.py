"""Serialize equation display traces onto presentation and API output blocks."""

from __future__ import annotations

from typing import Any

from engine.reference.parameter_value_source import apply_value_provenance_to_row
from models.equation_display_trace import EquationDisplayTrace
from models.task import Task
from engine.reference.standards_reader import StandardsReader


_INPUT_TABLE_COLUMNS: tuple[dict[str, Any], ...] = (
    {"key": "symbol", "label": "Symbol", "sortable": False},
    {"key": "definition", "label": "Definition", "sortable": False},
    {"key": "value", "label": "Value", "sortable": False},
)


def trace_to_dict(trace: EquationDisplayTrace) -> dict[str, Any]:
    return trace.to_dict()


def trace_from_dict(payload: dict[str, Any] | None) -> EquationDisplayTrace | None:
    if not isinstance(payload, dict):
        return None
    try:
        return EquationDisplayTrace.from_dict(payload)
    except (TypeError, ValueError):
        return None


def _input_table_from_trace(
    trace: EquationDisplayTrace,
    *,
    reader: StandardsReader | None = None,
    task: Task | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in trace.inputs:
        value_text = ""
        if item.value is not None:
            try:
                from api.equation_inputs_display import format_value_with_unit_for_display

                value_text = format_value_with_unit_for_display(item.value, item.unit) or ""
            except Exception:
                value_text = item.display_value or str(item.value)
        elif item.display_value:
            value_text = item.display_value

        row: dict[str, Any] = {
            "symbol": item.symbol,
            "definition": item.label,
            "value": value_text,
        }
        if item.parameter_id:
            row["parameter_id"] = item.parameter_id
        trace_source_type = str(item.source_type or "").strip() or None
        trace_source_ref = str(item.source_ref or "").strip() or None

        if reader is not None and task is not None and item.parameter_id:
            row = apply_value_provenance_to_row(
                row,
                reader,
                item.parameter_id,
                task,
                display_value=value_text,
                trace_source_type=trace_source_type,
                trace_source_ref=trace_source_ref,
            )
        elif not value_text:
            row["value"] = "Awaiting user input"
            row["value_status"] = "unresolved_user_input"
        rows.append(row)
    return {"columns": list(_INPUT_TABLE_COLUMNS), "rows": rows}


def enrich_equation_block(
    block: dict[str, Any],
    trace: EquationDisplayTrace | None,
    *,
    reader: StandardsReader | None = None,
    task: Task | None = None,
) -> dict[str, Any]:
    """Attach equation_display_trace and align legacy fields when evaluated."""
    if trace is None:
        return block

    enriched = dict(block)
    enriched["equation_display_trace"] = trace_to_dict(trace)

    if trace.status == "evaluated":
        if trace.substituted_latex:
            enriched["content"] = trace.substituted_latex
            enriched["display"] = trace.substituted_latex.replace("\\ ", " ").replace("\\mathrm{", "").replace("}", "")
        elif trace.symbolic_latex:
            enriched["content"] = trace.symbolic_latex
            enriched["display"] = trace.symbolic_latex

        enriched["input_table"] = _input_table_from_trace(trace, reader=reader, task=task)

        if trace.result is not None:
            enriched["result"] = {
                "label": trace.result.symbol,
                "value": trace.result.display_value,
                "unit": trace.result.unit or None,
            }
    elif trace.symbolic_latex:
        enriched.setdefault("content", trace.symbolic_latex)
        enriched.setdefault("display", trace.symbolic_latex)

    return enriched


def find_trace_for_equation(task: Task, equation_node_id: str) -> EquationDisplayTrace | None:
    trace_entries = task.outputs.get("_execution_trace")
    if not isinstance(trace_entries, list):
        return None

    for entry in trace_entries:
        if not isinstance(entry, dict):
            continue
        node_trace = entry.get("trace")
        if not isinstance(node_trace, dict):
            continue
        found = trace_from_dict(node_trace.get("equation_display_trace"))
        if found is None:
            continue
        entry_node_id = str(entry.get("node_id", ""))
        if entry_node_id == equation_node_id or found.equation_id == equation_node_id:
            return found
    return None


def find_trace_in_execution_payload(payload: dict[str, Any] | None) -> EquationDisplayTrace | None:
    if not isinstance(payload, dict):
        return None
    return trace_from_dict(payload.get("equation_display_trace"))
