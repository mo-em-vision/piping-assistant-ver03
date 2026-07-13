"""Performance trace metrics extraction and interactive-path span budgets."""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from tests.helpers.projection_performance_contract import (
    iter_spans,
    serializer_debug_projection_duration_ms,
)

# CI-friendly ceilings derived from profile_submit_input gate-submit baseline (~772 ms total).
INTERACTIVE_SUBMIT_TOTAL_BUDGET_MS = 15_000.0
GRAPH_BUILD_PLAN_BUDGET_MS = 3_000.0
GRAPH_PREVIEW_EVAL_BUDGET_MS = 5_000.0
PLANNER_PROJECTION_BUDGET_MS = 5_000.0
GOAL_TREE_REFRESH_BUDGET_MS = 5_000.0
TASK_STATE_SERIALIZATION_BUDGET_MS = 5_000.0
DISPLAY_OUTPUT_BUILD_BUDGET_MS = 3_000.0
INSPECTION_BUILD_MIN_MS = 1.0

PERFORMANCE_TABLE_ROWS: list[dict[str, Any]] = []


def span_duration_ms(
    trace: Mapping[str, Any],
    name: str,
    *,
    op_type: str | None = None,
) -> float:
    durations: list[float] = []
    for span in iter_spans(trace):
        if span.get("name") != name:
            continue
        if op_type is not None and span.get("op_type") != op_type:
            continue
        durations.append(float(span.get("duration_ms") or 0.0))
    return max(durations) if durations else 0.0


def collect_interactive_submit_metrics(trace: Mapping[str, Any]) -> dict[str, float]:
    return {
        "submit_input_total_ms": float(trace.get("total_duration_ms") or 0.0),
        "submit_input_span_ms": span_duration_ms(trace, "submit_input"),
        "task_state_span_ms": span_duration_ms(trace, "task_state"),
        "engineering_plan_projection_ms": span_duration_ms(trace, "engineering_plan_projection"),
        "display_output_projection_ms": span_duration_ms(trace, "display_output_projection"),
        "graph_build_plan_ms": span_duration_ms(trace, "graph_build_plan"),
        "graph_preview_eval_ms": span_duration_ms(trace, "graph_preview_eval"),
        "goal_tree_refresh_ms": span_duration_ms(trace, "goal_tree_refresh"),
        "serializer_debug_projection_ms": serializer_debug_projection_duration_ms(trace),
        "build_inspection_payload_ms": span_duration_ms(trace, "build_inspection_payload"),
    }


def collect_full_projection_metrics(trace: Mapping[str, Any]) -> dict[str, float]:
    return {
        "task_state_total_ms": float(trace.get("total_duration_ms") or 0.0),
        "task_state_span_ms": span_duration_ms(trace, "task_state"),
        "legacy_goal_map_projection_ms": span_duration_ms(trace, "legacy_goal_map_projection"),
        "engineering_plan_to_dict_ms": span_duration_ms(
            trace,
            "engineering_plan_to_dict",
            op_type="serializer",
        ),
        "engineering_plan_view_ms": span_duration_ms(trace, "engineering_plan_view"),
        "serializer_debug_projection_ms": serializer_debug_projection_duration_ms(trace),
    }


def collect_inspection_metrics(trace: Mapping[str, Any]) -> dict[str, float]:
    return {
        "inspection_total_ms": float(trace.get("total_duration_ms") or 0.0),
        "build_inspection_payload_ms": span_duration_ms(trace, "build_inspection_payload"),
        "get_inspection_span_ms": span_duration_ms(trace, "get_inspection"),
    }


def record_performance_row(
    *,
    behavior: str,
    test_name: str,
    metrics: Mapping[str, float | int | str | bool],
    passed: bool = True,
) -> None:
    PERFORMANCE_TABLE_ROWS.append(
        {
            "behavior": behavior,
            "test": test_name,
            "passed": passed,
            **dict(metrics),
        }
    )


def assert_interactive_gate_submit_span_budgets(
    trace: Mapping[str, Any],
    *,
    context: str,
) -> dict[str, float]:
    metrics = collect_interactive_submit_metrics(trace)

    assert metrics["submit_input_total_ms"] < INTERACTIVE_SUBMIT_TOTAL_BUDGET_MS, (
        f"{context}: submit_input total {metrics['submit_input_total_ms']:.1f} ms "
        f"(budget {INTERACTIVE_SUBMIT_TOTAL_BUDGET_MS:.0f} ms)"
    )
    if metrics["graph_build_plan_ms"] > 0:
        assert metrics["graph_build_plan_ms"] < GRAPH_BUILD_PLAN_BUDGET_MS, (
            f"{context}: graph_build_plan {metrics['graph_build_plan_ms']:.1f} ms"
        )
    if metrics["graph_preview_eval_ms"] > 0:
        assert metrics["graph_preview_eval_ms"] < GRAPH_PREVIEW_EVAL_BUDGET_MS, (
            f"{context}: graph_preview_eval {metrics['graph_preview_eval_ms']:.1f} ms"
        )
    if metrics["engineering_plan_projection_ms"] > 0:
        assert metrics["engineering_plan_projection_ms"] < PLANNER_PROJECTION_BUDGET_MS, (
            f"{context}: engineering_plan_projection "
            f"{metrics['engineering_plan_projection_ms']:.1f} ms"
        )
    if metrics["goal_tree_refresh_ms"] > 0:
        assert metrics["goal_tree_refresh_ms"] < GOAL_TREE_REFRESH_BUDGET_MS, (
            f"{context}: goal_tree_refresh {metrics['goal_tree_refresh_ms']:.1f} ms"
        )
    assert metrics["task_state_span_ms"] < TASK_STATE_SERIALIZATION_BUDGET_MS, (
        f"{context}: task_state {metrics['task_state_span_ms']:.1f} ms"
    )
    if metrics["display_output_projection_ms"] > 0:
        assert metrics["display_output_projection_ms"] < DISPLAY_OUTPUT_BUILD_BUDGET_MS, (
            f"{context}: display_output_projection "
            f"{metrics['display_output_projection_ms']:.1f} ms"
        )

    return metrics


def format_performance_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No performance metrics recorded."

    metric_keys = sorted(
        {
            key
            for row in rows
            for key in row
            if key not in {"behavior", "test", "passed"}
            and isinstance(row.get(key), (int, float))
        }
    )

    header = ["Behavior", "Test", "Pass"] + metric_keys
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    for row in rows:
        cells = [
            str(row.get("behavior", "")),
            str(row.get("test", "")),
            "yes" if row.get("passed", True) else "no",
        ]
        for key in metric_keys:
            value = row.get(key)
            if isinstance(value, float):
                cells.append(f"{value:.1f}")
            elif value is None:
                cells.append("—")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not PERFORMANCE_TABLE_ROWS:
        return
    terminal = session.config.pluginmanager.get_plugin("terminalreporter")
    if terminal is None:
        return
    terminal.write_sep("=", "Pipe wall performance metrics")
    terminal.write_line(format_performance_table(PERFORMANCE_TABLE_ROWS))
