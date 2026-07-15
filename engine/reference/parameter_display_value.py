"""Format parameter fact values for user-facing display (no messaging workflow logic)."""

from __future__ import annotations

from typing import Any

from engine.graph.resolution_branches import active_resolution_branch_id
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
    del reader
    canonical = canonical_parameter_key(parameter_id)
    inp = read_parameter_value(task_inputs, canonical)
    if inp is not None:
        direct = format_fact_display_value(inp)
        if direct is not None:
            if canonical == "outside_diameter":
                nps = read_parameter_value(task_inputs, "nominal_pipe_size")
                if (
                    nps is not None
                    and is_known_fact(nps)
                    and active_resolution_branch_id("outside_diameter", task_inputs) != "direct_od"
                ):
                    return f"{direct} (NPS {fact_scalar_value(nps)})"
            return direct

    if canonical == "outside_diameter":
        if active_resolution_branch_id("outside_diameter", task_inputs) == "direct_od":
            return None
        nps = read_parameter_value(task_inputs, "nominal_pipe_size")
        if nps is not None and is_known_fact(nps):
            return f"NPS {fact_scalar_value(nps)} (lookup pending)"
    return None
