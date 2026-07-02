"""Build per-node calculation summaries for the desktop right panel."""

from __future__ import annotations

from typing import Any

from api.equation_inputs_display import _SYMBOL_TO_INPUT_ID, _format_scalar, _format_unit_for_display
from api.output_blocks import _NODE_REFERENCES, _format_number
from engine.reference.standards_reader import StandardsReader
from models.fact import fact_scalar_value, fact_unit
from models.task import Task

_SYMBOL_LABELS: dict[str, str] = {
    "P": "Design pressure",
    "D": "Outside diameter",
    "S": "Allowable stress",
    "E": "Joint efficiency",
    "W": "Weld strength reduction",
    "Y": "Temperature coefficient",
    "t": "Required wall thickness",
    "t_m": "Minimum required thickness",
    "c": "Corrosion allowance",
}

_PRIMARY_OUTPUT_KEYS: tuple[tuple[str, str, str], ...] = (
    ("t", "t", "Required wall thickness"),
    ("required_thickness", "t", "Required wall thickness"),
    ("minimum_required_thickness", "t_m", "Minimum required thickness"),
    ("t_m", "t_m", "Minimum required thickness"),
    ("S", "S", "Allowable stress"),
    ("allowable_stress", "S", "Allowable stress"),
)


def build_node_calculation_summaries(
    task: Task,
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    trace = task.outputs.get("_execution_trace")
    if not isinstance(trace, list):
        return []

    summaries: list[dict[str, Any]] = []
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id") or "")
        if not node_id:
            continue
        try:
            record = reader.load(node_id)
        except FileNotFoundError:
            continue
        node_type = str(record.metadata.get("type", ""))
        if node_type not in {"calculation", "lookup", "equation"}:
            continue

        node_trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
        outputs = entry.get("outputs") if isinstance(entry.get("outputs"), dict) else {}
        calculation = node_trace.get("calculation")
        lookup = node_trace.get("lookup")
        substitution = node_trace.get("substitution")

        if node_type == "calculation" and not isinstance(calculation, dict):
            continue
        if node_type == "lookup" and not isinstance(lookup, dict):
            continue
        if node_type == "equation" and not substitution and not isinstance(calculation, dict):
            continue

        primary = _primary_result(outputs)
        if primary is None:
            continue

        reference = _NODE_REFERENCES.get(node_id, {})
        paragraph = str(reference.get("paragraph") or record.metadata.get("paragraph") or "").strip() or None
        title = str(
            reference.get("title")
            or record.metadata.get("title")
            or node_id
        ).strip()

        inputs = _input_rows(task, node_trace, entry.get("inputs") if isinstance(entry.get("inputs"), dict) else {})

        summaries.append(
            {
                "node_id": node_id,
                "paragraph": paragraph,
                "title": title,
                "primary_result": primary,
                "inputs": inputs,
            }
        )

    return summaries


def _primary_result(outputs: dict[str, Any]) -> dict[str, str] | None:
    for key, symbol, label in _PRIMARY_OUTPUT_KEYS:
        if key not in outputs or outputs[key] is None:
            continue
        unit_key = f"{key}_unit"
        unit = str(outputs.get(unit_key) or task_output_unit(key))
        return {
            "symbol": symbol,
            "label": label,
            "value": _format_number(outputs[key]),
            "unit": unit,
        }
    return None


def task_output_unit(key: str) -> str:
    if key in {"S", "allowable_stress"}:
        return "Pa"
    if key in {"t", "required_thickness", "minimum_required_thickness", "t_m"}:
        return "mm"
    return ""


def _input_rows(
    task: Task,
    node_trace: dict[str, Any],
    resolved_inputs: dict[str, Any],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    variables_si = node_trace.get("variables_si")
    if isinstance(variables_si, dict):
        for symbol, raw_value in variables_si.items():
            symbol_key = str(symbol)
            if symbol_key in seen or not isinstance(raw_value, (int, float)):
                continue
            seen.add(symbol_key)
            rows.append(_row_for_symbol(task, symbol_key, float(raw_value), resolved_inputs))

    if not rows and resolved_inputs:
        for key, value in resolved_inputs.items():
            if key in {"thin_wall"} or not isinstance(value, (int, float)):
                continue
            symbol_key = str(key)
            if symbol_key in seen:
                continue
            seen.add(symbol_key)
            rows.append(_row_for_symbol(task, symbol_key, float(value), resolved_inputs))

    return rows


def _row_for_symbol(
    task: Task,
    symbol: str,
    si_value: float,
    resolved_inputs: dict[str, Any],
) -> dict[str, str]:
    input_id = _SYMBOL_TO_INPUT_ID.get(symbol, symbol)
    fact = task.fact_store.active_fact(input_id)
    unit = ""
    display_value = _format_number(si_value)

    if fact is not None and fact_scalar_value(fact) is not None:
        display_value = _format_scalar(fact_scalar_value(fact))
        fact_unit_value = fact_unit(fact)
        if fact_unit_value and fact_unit_value not in {"dimensionless", "Pa"}:
            unit = _format_unit_for_display(fact_unit_value)
        elif symbol in resolved_inputs:
            unit_key = f"{symbol}_unit"
            if unit_key in resolved_inputs:
                unit = _format_unit_for_display(str(resolved_inputs[unit_key]))
    elif symbol in resolved_inputs:
        display_value = _format_number(resolved_inputs[symbol])
        unit_key = f"{symbol}_unit"
        if unit_key in resolved_inputs:
            unit = _format_unit_for_display(str(resolved_inputs[unit_key]))

    if symbol == "S" and si_value > 1_000_000:
        display_value = _format_number(si_value / 1_000_000)
        unit = "MPa"

    name = _SYMBOL_LABELS.get(symbol, symbol.replace("_", " ").title())
    return {
        "symbol": symbol,
        "name": name,
        "value": display_value,
        "unit": unit,
    }
