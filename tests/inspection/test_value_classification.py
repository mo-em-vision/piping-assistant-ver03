"""Tests for inspection value classification."""

from __future__ import annotations

from engine.inspection.value_classification import (
    InspectionValueDestination,
    classify_inspection_value,
    is_inspection_excluded_output_key,
)


def test_debug_output_keys_are_excluded_from_parameters() -> None:
    for key in (
        "engineering_plan",
        "engineering_plan_view",
        "planner_inspector_summary",
        "graph_navigation",
        "_plan_edges",
        "_planner_decisions",
        "_skipped_trace",
    ):
        assert is_inspection_excluded_output_key(key)


def test_classify_planner_debug_objects() -> None:
    assert (
        classify_inspection_value(
            "engineering_plan",
            {"value": {"plan_id": "PLAN-1"}, "source": "derived"},
        )
        == InspectionValueDestination.PLANNER_DEBUG
    )
    assert classify_inspection_value("_skipped_trace", {"value": []}) == InspectionValueDestination.TRACE


def test_classify_scalar_engineering_fact() -> None:
    assert (
        classify_inspection_value(
            "design_temperature",
            {
                "value": 200,
                "display_value": "200 degF",
                "source": "user_input",
                "parameter_node_id": "PARAM-design-temperature",
            },
        )
        == InspectionValueDestination.MAIN_FACTS
    )


def test_classify_equation_output() -> None:
    assert (
        classify_inspection_value(
            "minimum_required_thickness",
            {
                "value": 0.25,
                "display_value": "0.25 in",
                "source": "equation",
                "parameter_node_id": "PARAM-minimum-required-thickness",
            },
        )
        == InspectionValueDestination.OUTPUTS
    )


def test_unformatted_dict_without_param_node_is_planner_debug() -> None:
    assert (
        classify_inspection_value(
            "custom_blob",
            {"value": {"nested": True}, "source": "derived"},
        )
        == InspectionValueDestination.PLANNER_DEBUG
    )
