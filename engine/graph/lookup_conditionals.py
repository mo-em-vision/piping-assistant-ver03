"""Interpret lookup_conditionals authored on global PARAM-* output nodes."""

from __future__ import annotations

from typing import Any

from engine.reference.parameter_keys import load_parameter_node_metadata


def lookup_conditionals_for_parameter(
    param_node_id: str,
    *,
    store: Any | None = None,
) -> dict[str, Any]:
    """Return lookup_conditionals from a parameter node (graph metadata or live YAML)."""
    if store is not None:
        node = store.get_node(param_node_id)
        if node is not None:
            conditionals = node.metadata.get("lookup_conditionals")
            if isinstance(conditionals, dict) and conditionals:
                return conditionals

    metadata = load_parameter_node_metadata(param_node_id)
    if metadata is None:
        return {}
    conditionals = metadata.get("lookup_conditionals")
    return conditionals if isinstance(conditionals, dict) else {}


def _convert_lookup_input(value: float, from_unit: str, to_unit: str) -> float:
    from engine.units.unit_resolver import get_unit_resolver

    resolver = get_unit_resolver()
    target = to_unit.replace("UNIT-", "") if to_unit.startswith("UNIT-") else to_unit
    converted, _ = resolver.convert_value(float(value), from_unit, target)
    return float(converted)


def apply_lookup_conditional_bounds(value: float, rules: dict[str, Any]) -> float:
    """Clamp a lookup input already expressed in the conditional unit."""
    bounded = float(value)
    min_value = rules.get("min")
    max_value = rules.get("max")
    if min_value is not None and bounded < float(min_value):
        if str(rules.get("below_min", "")).strip() == "use_min":
            bounded = float(min_value)
    if max_value is not None and bounded > float(max_value):
        if str(rules.get("above_max", "")).strip() == "use_max":
            bounded = float(max_value)
    return bounded


def bounded_lookup_input_value(
    value: float,
    *,
    input_key: str,
    input_unit: str,
    conditionals: dict[str, Any],
) -> float:
    """Convert a lookup key to the conditional unit and apply authored bounds."""
    rules = conditionals.get(input_key)
    if not isinstance(rules, dict):
        return value

    target_unit = str(rules.get("unit") or input_unit).strip()
    converted = _convert_lookup_input(value, input_unit, target_unit)
    return apply_lookup_conditional_bounds(converted, rules)


def apply_lookup_conditionals_to_inputs(
    inputs: dict[str, Any],
    conditionals: dict[str, Any],
    *,
    unit_suffix: str = "_unit",
) -> dict[str, Any]:
    """Return a copy of lookup inputs with conditional bounds applied."""
    if not conditionals:
        return dict(inputs)

    adjusted = dict(inputs)
    for input_key, rules in conditionals.items():
        if input_key not in adjusted or not isinstance(rules, dict):
            continue
        unit_key = f"{input_key}{unit_suffix}"
        input_unit = str(adjusted.get(unit_key) or "F")
        adjusted[input_key] = bounded_lookup_input_value(
            float(adjusted[input_key]),
            input_key=input_key,
            input_unit=input_unit,
            conditionals=conditionals,
        )
        if unit_key in adjusted and rules.get("unit"):
            adjusted[unit_key] = str(rules["unit"]).replace("UNIT-", "")
    return adjusted


def resolve_lookup_input_value(
    value: float,
    *,
    input_key: str,
    input_unit: str,
    output_param_node_id: str,
    table_unit: str = "F",
    store: Any | None = None,
) -> float:
    """Apply PARAM lookup_conditionals or convert to the table temperature unit."""
    conditionals = lookup_conditionals_for_parameter(output_param_node_id, store=store)
    if isinstance(conditionals.get(input_key), dict):
        return bounded_lookup_input_value(
            value,
            input_key=input_key,
            input_unit=input_unit,
            conditionals=conditionals,
        )
    from engine.executor.unit_manager import convert_to_si

    converted, _ = convert_to_si(value, input_unit, target_unit=table_unit.lower())
    return float(converted)
