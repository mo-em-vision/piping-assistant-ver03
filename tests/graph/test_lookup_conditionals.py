"""Tests for graph-authored lookup_conditionals on PARAM output nodes."""

from __future__ import annotations

from engine.graph.lookup_conditionals import (
    apply_lookup_conditional_bounds,
    bounded_lookup_input_value,
    lookup_conditionals_for_parameter,
    resolve_lookup_input_value,
)


def test_y_parameter_lookup_conditionals_from_yaml() -> None:
    conditionals = lookup_conditionals_for_parameter("PARAM-temperature-coefficient-Y")
    design_temp = conditionals["design_temperature"]
    assert design_temp["min"] == 900
    assert design_temp["max"] == 1250
    assert design_temp["below_min"] == "use_min"
    assert design_temp["above_max"] == "use_max"


def test_apply_lookup_conditional_bounds() -> None:
    rules = {"min": 900, "max": 1250, "below_min": "use_min", "above_max": "use_max"}
    assert apply_lookup_conditional_bounds(100.0, rules) == 900.0
    assert apply_lookup_conditional_bounds(975.0, rules) == 975.0
    assert apply_lookup_conditional_bounds(1500.0, rules) == 1250.0


def test_bounded_lookup_input_value_converts_and_clamps() -> None:
    conditionals = lookup_conditionals_for_parameter("PARAM-temperature-coefficient-Y")
    assert bounded_lookup_input_value(
        100.0,
        input_key="design_temperature",
        input_unit="F",
        conditionals=conditionals,
    ) == 900.0


def test_resolve_lookup_input_value_without_conditionals_converts_to_table_unit() -> None:
    resolved = resolve_lookup_input_value(
        200.0,
        input_key="design_temperature",
        input_unit="F",
        output_param_node_id="PARAM-allowable-stress",
        table_unit="F",
    )
    assert resolved == 200.0


def test_resolve_lookup_input_value_applies_y_conditionals() -> None:
    assert resolve_lookup_input_value(
        100.0,
        input_key="design_temperature",
        input_unit="F",
        output_param_node_id="PARAM-temperature-coefficient-Y",
        table_unit="F",
    ) == 900.0
