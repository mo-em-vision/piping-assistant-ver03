"""Unit conversion and validation before calculation execution."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from models.input import EngineeringInput

PSI_TO_PA = 6894.757293168
BAR_TO_PA = 100_000.0
IN_TO_MM = 25.4


def fahrenheit_to_kelvin(value: float) -> float:
    return (value - 32.0) * 5.0 / 9.0 + 273.15


def celsius_to_kelvin(value: float) -> float:
    return value + 273.15


def normalize_unit(unit: str) -> str:
    return unit.strip().lower()


def _convert_via_resolver(
    value: float,
    unit: str,
    *,
    target_unit: str | None = None,
) -> tuple[float, str] | None:
    try:
        from engine.units.unit_resolver import get_unit_resolver

        resolver = get_unit_resolver()
        from_id = resolver.resolve_unit_id(unit)
        if from_id is None:
            return None

        dim = resolver.dimension(from_id)
        if dim == "dimensionless" or normalize_unit(unit) in ("dimensionless", "1", ""):
            return value, "dimensionless"

        if target_unit:
            target_key = normalize_unit(target_unit)
            if target_key in ("f", "degf", "°f"):
                converted, _ = resolver.convert_value(value, unit, "degF")
                return converted, "F"
            converted, symbol = resolver.convert_value(value, unit, target_unit)
            return converted, symbol

        si_value, si_symbol = resolver.convert_to_canonical_si(value, unit, dimension=dim)
        return si_value, si_symbol
    except (ValueError, OSError, ImportError):
        return None


def _convert_legacy(
    value: float,
    unit: str,
    *,
    target_unit: str | None = None,
) -> tuple[float, str]:
    u = normalize_unit(unit)
    target = normalize_unit(target_unit) if target_unit else None

    if u in ("pa",):
        return value, "Pa"
    if u in ("mm",):
        return value, "mm"
    if u in ("dimensionless", "1", ""):
        return value, "dimensionless"
    if u in ("k",):
        return value, "K"

    if u in ("psi",):
        return value * PSI_TO_PA, "Pa"
    if u in ("bar",):
        return value * BAR_TO_PA, "Pa"
    if u in ("in",):
        return value * IN_TO_MM, "mm"
    if u in ("f", "degf", "°f"):
        if target == "f":
            return value, "F"
        return fahrenheit_to_kelvin(value), "K"
    if u in ("c", "degc", "°c"):
        if target == "f":
            return (value * 9.0 / 5.0) + 32.0, "F"
        return celsius_to_kelvin(value), "K"

    if target:
        return value, target
    return value, unit


def convert_to_si(value: float, unit: str, *, target_unit: str | None = None) -> tuple[float, str]:
    """Convert a numeric value to SI for calculation."""
    resolved = _convert_via_resolver(value, unit, target_unit=target_unit)
    if resolved is not None:
        return resolved
    return _convert_legacy(value, unit, target_unit=target_unit)


def prepare_engineering_input(
    engineering_input: EngineeringInput,
    *,
    target_unit: str | None = None,
) -> EngineeringInput:
    """Return input with SI value while preserving original units."""
    if not isinstance(engineering_input.value, (int, float)):
        return engineering_input

    original_value = (
        engineering_input.original_value
        if engineering_input.original_value is not None
        else engineering_input.value
    )
    original_unit = engineering_input.original_unit or engineering_input.unit

    si_value, si_unit = convert_to_si(
        float(engineering_input.value),
        engineering_input.unit,
        target_unit=target_unit,
    )

    return replace(
        engineering_input,
        value=si_value,
        unit=si_unit,
        original_value=original_value,
        original_unit=original_unit,
    )


def prepare_symbol_map(
    raw_values: dict[str, Any],
    unit_map: dict[str, str],
    *,
    target_units: dict[str, str] | None = None,
) -> dict[str, float]:
    """Convert a symbol map to SI floats for expression evaluation."""
    result: dict[str, float] = {}
    targets = target_units or {}

    for symbol, value in raw_values.items():
        if not isinstance(value, (int, float)):
            continue
        unit = unit_map.get(symbol, "dimensionless")
        converted, _ = convert_to_si(float(value), unit, target_unit=targets.get(symbol))
        result[symbol] = converted

    return result
