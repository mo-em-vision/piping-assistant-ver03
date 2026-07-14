"""Serialize equation display traces onto presentation and API output blocks."""

from __future__ import annotations

from typing import Any

from engine.equation.input_table import (
    INPUT_TABLE_COLUMNS,
    equation_parameter_description,
    equation_parameter_name,
    finalize_equation_input_table_row,
    format_value_for_table,
)
from engine.reference.parameter_value_source import apply_value_provenance_to_row
from models.calculation import CalculationResult
from models.equation_display_trace import EquationDisplayTrace
from models.task import Task
from engine.reference.standards_reader import StandardsReader


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
        param_id = str(item.parameter_id or "").strip()
        value_text, unit_text = format_value_for_table(item.value, item.unit)
        if not value_text and item.display_value:
            value_text = str(item.display_value).strip()

        row: dict[str, Any] = {
            "symbol": item.symbol,
            "parameter": equation_parameter_name(reader, param_id) if reader and param_id else "",
            "description": equation_parameter_description(reader, param_id) if reader and param_id else "",
            "definition": equation_parameter_description(reader, param_id) if reader and param_id else "",
            "value": value_text,
            "unit": unit_text,
            "source": "",
        }
        if param_id:
            row["parameter_id"] = param_id
        trace_source_type = str(item.source_type or "").strip() or None
        trace_source_ref = str(item.source_ref or "").strip() or None

        if reader is not None and task is not None and param_id:
            row = apply_value_provenance_to_row(
                row,
                reader,
                param_id,
                task,
                display_value=value_text,
                trace_source_type=trace_source_type,
                trace_source_ref=trace_source_ref,
            )
            from api.equation_evaluation_display import _definition_reference_for_parameter

            definition_reference = _definition_reference_for_parameter(reader, param_id)
            if definition_reference is not None:
                row["definition_reference"] = definition_reference
        elif not value_text:
            if trace.status == "evaluated":
                row["value"] = item.display_value or "—"
                row["value_status"] = "resolved"
            else:
                from api.equation_inputs_display import AWAITING_USER_INPUT

                row["value"] = AWAITING_USER_INPUT
                row["value_status"] = "unresolved_user_input"
        rows.append(finalize_equation_input_table_row(row))
    return {"columns": list(INPUT_TABLE_COLUMNS), "rows": rows}


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
    enriched.setdefault("display_role", "equation")
    enriched["equation_display_trace"] = trace_to_dict(trace)

    if trace.title and not str(enriched.get("title") or "").strip():
        enriched["title"] = trace.title

    if trace.status == "evaluated":
        enriched["display_state"] = "evaluated"
        enriched["equation_content"] = "evaluated"
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
        enriched.setdefault("display_state", "preview")
        if trace.substituted_latex:
            enriched["equation_content"] = "substituted"
        else:
            enriched.setdefault("equation_content", "symbolic")

    from models.display_role import infer_equation_content, lifecycle_for_equation_state

    if enriched.get("display_role") == "equation":
        enriched.setdefault("equation_content", infer_equation_content(enriched))
        state = str(enriched.get("display_state") or "preview")
        enriched["lifecycle"] = lifecycle_for_equation_state(state)

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


def record_equation_execution_trace(
    task: Task,
    reader: StandardsReader,
    *,
    equation_node_id: str,
    source_node_id: str,
    equation_metadata: dict[str, Any],
    symbol_values: dict[str, float],
    calculation: CalculationResult | None = None,
    render_steps: Any | None = None,
) -> None:
    """Append or update an execution-trace entry with equation_display_trace."""
    from engine.equation.equation_display_trace_builder import build_equation_display_trace
    from api.equation_display_registry import register_equation_display_key, source_node_id_for_equation

    resolved_source = str(source_node_id or "").strip() or source_node_id_for_equation(
        reader, equation_node_id
    )
    display_trace = build_equation_display_trace(
        reader=reader,
        equation_id=equation_node_id,
        equation_metadata=equation_metadata,
        symbol_values=symbol_values,
        source_node_id=resolved_source,
        dependency_outputs=dict(task.outputs),
        task_inputs=task.fact_store.active_facts(),
        calculation=calculation,
        render_steps=render_steps,
        task=task,
    )

    trace_payload: dict[str, Any] = {"equation_display_trace": display_trace.to_dict()}
    if calculation is not None:
        final = calculation.final_result
        if final is not None:
            trace_payload["calculation"] = {
                "final_result": {
                    "symbol": final.symbol,
                    "value": final.value,
                    "unit": final.unit,
                }
            }

    entries = task.outputs.get("_execution_trace")
    if not isinstance(entries, list):
        entries = []
    updated = False
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        entry_node_id = str(entry.get("node_id") or "")
        existing = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        existing_trace = trace_from_dict(existing.get("equation_display_trace"))
        if entry_node_id == equation_node_id or (
            existing_trace is not None and existing_trace.equation_id == equation_node_id
        ):
            merged = dict(existing)
            merged.update(trace_payload)
            entries[index] = {"node_id": equation_node_id, "trace": merged}
            updated = True
            break
    if not updated:
        entries.append({"node_id": equation_node_id, "trace": trace_payload})
    task.outputs["_execution_trace"] = entries

    workflow_id = str(task.outputs.get("workflow") or "").strip()
    if workflow_id:
        register_equation_display_key(task, workflow_id, resolved_source, equation_node_id)
