"""Unit tests for projection performance contract helpers."""

from __future__ import annotations

import pytest
from _pytest.outcomes import Failed

from tests.helpers.projection_performance_contract import (
    assert_interactive_trace_projection_budget,
    assert_interactive_trace_skips_debug_projection_spans,
    assert_trace_rebuilds_inspection_debug_projections,
    serializer_debug_projection_duration_ms,
)


def test_interactive_trace_rejects_serializer_debug_spans() -> None:
    trace = {
        "spans": [
            {
                "name": "legacy_goal_map_projection",
                "op_type": "serializer",
                "duration_ms": 12.0,
            }
        ]
    }
    with pytest.raises(Failed):
        assert_interactive_trace_skips_debug_projection_spans(trace, context="unit")


def test_interactive_trace_allows_planner_engineering_plan_to_dict() -> None:
    trace = {
        "spans": [
            {
                "name": "engineering_plan_to_dict",
                "op_type": "planner",
                "duration_ms": 40.0,
            }
        ]
    }
    assert_interactive_trace_skips_debug_projection_spans(trace, context="unit")


def test_interactive_trace_budget_requires_interactive_engineering_plan_projection() -> None:
    trace = {
        "spans": [
            {
                "name": "engineering_plan_projection",
                "op_type": "serializer",
                "duration_ms": 25.0,
                "notes": "mode=interactive",
            }
        ]
    }
    assert_interactive_trace_projection_budget(trace, context="unit")


def test_inspection_trace_requires_build_inspection_payload() -> None:
    trace = {"spans": [{"name": "get_inspection", "op_type": "api", "duration_ms": 1.0}]}
    with pytest.raises(AssertionError):
        assert_trace_rebuilds_inspection_debug_projections(trace, context="unit")

    trace = {
        "spans": [
            {"name": "build_inspection_payload", "op_type": "serializer", "duration_ms": 80.0}
        ]
    }
    assert_trace_rebuilds_inspection_debug_projections(trace, context="unit")


def test_serializer_debug_projection_duration_sums_only_serializer_spans() -> None:
    trace = {
        "spans": [
            {"name": "engineering_plan_view", "op_type": "serializer", "duration_ms": 10.0},
            {"name": "engineering_plan_view", "op_type": "planner", "duration_ms": 99.0},
        ]
    }
    assert serializer_debug_projection_duration_ms(trace) == 10.0
