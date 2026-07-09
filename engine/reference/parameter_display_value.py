"""Format parameter fact values for user-facing display (no messaging workflow logic)."""

from __future__ import annotations

from typing import Any

from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
from engine.graph.assumption_checker import field_value
from engine.reference.parameter_keys import canonical_parameter_key, read_parameter_value
from engine.reference.standards_reader import StandardsReader
from models.fact import Fact, FactClass, ValidationStatus, fact_scalar_value, fact_unit


def format_scalar_display(value: Any) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def is_known_fact(inp: Fact) -> bool:
    if inp.requires_confirmation and inp.fact_class == FactClass.DEFAULT_CONFIRMED:
        if inp.validation.status == ValidationStatus.PENDING:
            return False
    if inp.fact_class == FactClass.DEFAULT_CONFIRMED and inp.validation.status == ValidationStatus.PENDING:
        return False
    return fact_scalar_value(inp) is not None


def format_fact_display_value(inp: Fact) -> str | None:
    """Return a display string for a resolved fact, including units when present."""
    if not is_known_fact(inp):
        return None
    value = fact_scalar_value(inp)
    if value is None:
        return None
    unit = inp.original_unit or fact_unit(inp)
    if unit and unit != "dimensionless":
        return f"{format_scalar_display(value)} {unit}"
    return format_scalar_display(value)


def resolve_parameter_display_value(
    reader: StandardsReader,
    parameter_id: str,
    task_inputs: dict[str, Fact],
) -> str | None:
    """Resolve a display value for a parameter key from task facts."""
    canonical = canonical_parameter_key(parameter_id)
    inp = read_parameter_value(task_inputs, canonical)
    if inp is not None:
        direct = format_fact_display_value(inp)
        if direct is not None:
            return direct

    if canonical == "outside_diameter":
        return _outside_diameter_from_nominal_pipe_size(reader, task_inputs)
    return None


def _outside_diameter_from_nominal_pipe_size(
    reader: StandardsReader,
    task_inputs: dict[str, Fact],
) -> str | None:
    mode = field_value("d_input_mode", task_inputs)
    if mode == "direct_od":
        return None
    nps = read_parameter_value(task_inputs, "nominal_pipe_size")
    if nps is None or not is_known_fact(nps):
        return None
    try:
        lookup = PipeDimensionLookup(reader.standards_root)
        result = lookup.lookup(str(fact_scalar_value(nps)))
        return f"{result.outside_diameter_mm} mm (NPS {fact_scalar_value(nps)})"
    except (ValueError, FileNotFoundError):
        return f"NPS {fact_scalar_value(nps)} (lookup pending)"
