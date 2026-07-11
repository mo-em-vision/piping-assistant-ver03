"""Shared equation input table column schema and row projection."""

from __future__ import annotations

from typing import Any

from engine.reference.parameter_keys import (
    parameter_display_label,
    parameter_node_description,
)
from engine.reference.parameter_value_source import AWAITING_USER_INPUT
from engine.reference.standards_reader import StandardsReader
from models.fact import Fact, FactClass, ValidationStatus, fact_scalar_value, fact_unit
from models.task import Task

_HIDDEN_UNITS = frozenset({"dimensionless", ""})

INPUT_TABLE_COLUMNS: tuple[dict[str, Any], ...] = (
    {"key": "symbol", "label": "Symbol", "sortable": False},
    {"key": "parameter", "label": "Parameter", "sortable": False},
    {"key": "description", "label": "Description", "sortable": False},
    {"key": "value", "label": "Value", "sortable": False},
    {"key": "unit", "label": "Unit", "sortable": False},
    {"key": "source", "label": "Source", "sortable": False},
)


def _format_unit_for_display(unit: str) -> str:
    normalized = unit.strip().lower()
    if normalized == "c":
        return "\u00b0C"
    if normalized == "f":
        return "\u00b0F"
    if normalized == "k":
        return "K"
    return unit


def _fact_has_displayable_value(fact: Fact | None) -> bool:
    if fact is None:
        return False
    if fact_scalar_value(fact) is None:
        return False
    if fact.fact_class == FactClass.DEFAULT_CONFIRMED and fact.validation.status == ValidationStatus.PENDING:
        return False
    return True


def equation_parameter_name(reader: StandardsReader, param_id: str) -> str:
    """Display label from linked PARAM ``name`` only."""
    param_id = str(param_id or "").strip()
    if not param_id:
        return ""
    return parameter_display_label(param_id, reader=reader)


def equation_parameter_description(reader: StandardsReader, param_id: str) -> str:
    """Description from linked PARAM ``description`` only; empty when missing."""
    param_id = str(param_id or "").strip()
    if not param_id:
        return ""
    text = parameter_node_description(reader=reader, param_id=param_id).strip()
    if not text:
        return ""
    try:
        meta = reader.load(param_id).metadata
        key = str(meta.get("key") or meta.get("input_id") or "").strip()
        if text == param_id or text == key:
            return ""
    except FileNotFoundError:
        if text == param_id:
            return ""
    return text


def format_value_for_table(value: Any, unit: str | None) -> tuple[str, str]:
    """Split numeric/text value and engineering unit for separate table columns."""
    if value is None:
        return "", ""

    from engine.equation.latex_format import format_numeric_display

    if isinstance(value, bool):
        value_text = str(value)
    elif isinstance(value, int):
        value_text = format_numeric_display(float(value))
    elif isinstance(value, float):
        value_text = format_numeric_display(value)
    else:
        value_text = str(value).strip()

    unit_text = ""
    if unit and str(unit).strip() not in _HIDDEN_UNITS:
        unit_text = _format_unit_for_display(str(unit).strip())

    return value_text, unit_text


def source_column_text(row: dict[str, Any]) -> str:
    """Plain-text Source column from value_provenance (chips rendered separately)."""
    provenance = row.get("value_provenance")
    if not isinstance(provenance, dict):
        return ""

    status = str(provenance.get("status") or "")
    source_type = str(provenance.get("source_type") or "")
    label = str(provenance.get("label") or "").strip()

    if status == "awaiting_user_input":
        return ""
    if status == "resolved" and source_type == "user_input":
        return "User input"
    if label and label != AWAITING_USER_INPUT:
        return label
    if status == "pending_derived" and source_type == "table_lookup":
        return "Table lookup"
    if status == "pending_derived" and source_type == "equation_output":
        return "Equation output"
    return ""


def finalize_equation_input_table_row(row: dict[str, Any]) -> dict[str, Any]:
    """Ensure canonical six-column row fields; keep legacy ``definition`` in sync."""
    updated = dict(row)

    description = str(updated.get("description") or updated.get("definition") or "").strip()
    updated["description"] = description
    if description:
        updated["definition"] = description

    if "parameter" not in updated:
        updated["parameter"] = ""

    if "unit" not in updated:
        updated["unit"] = ""

    updated["source"] = source_column_text(updated)
    return updated


def build_base_input_row(
    *,
    reader: StandardsReader,
    symbol: str,
    param_id: str,
) -> dict[str, Any]:
    """Build symbol/parameter/description fields without value or provenance."""
    param_id = str(param_id or "").strip()
    return {
        "symbol": symbol,
        "parameter": equation_parameter_name(reader, param_id) if param_id else "",
        "description": equation_parameter_description(reader, param_id) if param_id else "",
        "definition": equation_parameter_description(reader, param_id) if param_id else "",
        "value": "",
        "unit": "",
        "source": "",
        "parameter_id": param_id or None,
    }


def param_unit_from_metadata(reader: StandardsReader, param_id: str) -> str:
    if not param_id:
        return ""
    try:
        param = reader.load(param_id)
    except FileNotFoundError:
        return ""
    unit = str(param.metadata.get("unit") or param.metadata.get("canonical_unit") or "").strip()
    return unit if unit not in _HIDDEN_UNITS else ""


def resolve_row_value_parts(
    task: Task,
    reader: StandardsReader,
    *,
    param_id: str,
    input_id: str | None,
    symbol: str,
) -> tuple[str, str, str]:
    """Return (value, unit, display_for_provenance)."""
    from api.equation_evaluation_display import _output_display_value
    from api.equation_inputs_display import _input_display_value
    from engine.reference.parameter_keys import active_fact_for_key

    display = None
    if input_id:
        display = _input_display_value(task, input_id) or _output_display_value(task, input_id)

    metadata_unit = param_unit_from_metadata(reader, param_id)

    if input_id:
        fact = active_fact_for_key(task, input_id)
        if fact is not None and _fact_has_displayable_value(fact):
            scalar = fact_scalar_value(fact)
            fact_unit_text = fact_unit(fact) or metadata_unit
            value_text, unit_text = format_value_for_table(scalar, fact_unit_text)
            provenance_display = display or value_text
            if value_text:
                return value_text, unit_text, provenance_display

    if display:
        if metadata_unit and display.endswith(f" {metadata_unit}"):
            value_text = display[: -len(metadata_unit) - 1].strip()
            return value_text, metadata_unit, display
        return display, metadata_unit, display

    output_value = _output_display_value(task, input_id) if input_id else None
    if output_value is None and symbol:
        raw = task.outputs.get(symbol)
        if isinstance(raw, (int, float)):
            value_text, unit_text = format_value_for_table(raw, metadata_unit)
            return value_text, unit_text, output_value or value_text

    return "", metadata_unit, display or ""
