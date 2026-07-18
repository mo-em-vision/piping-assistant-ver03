"""Tests for append-only expansion traversal trace."""

from __future__ import annotations

from datetime import datetime, timezone

from engine.graph.expansion_traversal_trace import (
    TRACE_OUTPUT_KEY,
    append_expansion_step,
    append_parameter_resolved_step,
    inputs_fingerprint,
    load_expansion_trace,
    record_planning_refresh_trace,
    replay_active_node_order,
    trace_steps_to_traversal_events,
)
from engine.graph.traversal_reasons import (
    EXCLUSION_REASON_SUPERSEDED_BY_SELECTED_BRANCH,
    QUEUE_REASON_WAITING_FOR_DEPENDENCY,
    QUEUE_REASON_WAITING_FOR_USER_INPUT,
    normalize_exclusion_reason,
    normalize_queue_reason,
)
from models.execution import ExecutionPlan
from models.graph import GraphVersion


def _preview(active_nodes: list[str], *, skipped: list[dict] | None = None) -> ExecutionPlan:
    return ExecutionPlan(
        task_id="trace-test",
        root="pipe_wall_thickness_design",
        nodes=tuple(active_nodes),
        execution_order=tuple(active_nodes),
        inputs={},
        dependencies=(),
        graph_version=GraphVersion(
            graph_id="pipe_wall_thickness_design",
            created=datetime.now(timezone.utc),
            standard_versions={},
            nodes=tuple(active_nodes),
            edges=(),
        ),
        skipped_nodes=tuple(skipped or []),
    )


def test_queue_and_exclusion_reason_normalization() -> None:
    assert normalize_queue_reason("awaiting user input") == QUEUE_REASON_WAITING_FOR_USER_INPUT
    assert (
        normalize_queue_reason("awaiting parameter gathering")
        == "waiting_for_upstream_equation"
    )
    assert normalize_exclusion_reason("excluded by branch") == (
        EXCLUSION_REASON_SUPERSEDED_BY_SELECTED_BRANCH
    )
    assert normalize_exclusion_reason("not applicable") == "not_applicable"


def test_expansion_trace_appends_across_refreshes() -> None:
    outputs: dict = {}
    inputs_a = {"straight_pipe_section": True}
    inputs_b = {**inputs_a, "pressure_design_case": "internal_pressure"}

    record_planning_refresh_trace(
        outputs,
        root_id="pipe_wall_thickness_design",
        preview=_preview(["WF-ROOT", "304.1.1-a"]),
        path_decision=None,
        existing_inputs=inputs_a,
        lazy=True,
        pending_fields=["pressure_design_case"],
    )
    first_len = len(load_expansion_trace(outputs))

    record_planning_refresh_trace(
        outputs,
        root_id="pipe_wall_thickness_design",
        preview=_preview(["WF-ROOT", "304.1.1-a", "304.1.2-a"]),
        path_decision={"field": "pressure_design_case", "value": "internal_pressure", "selected_node": "304.1.2-a"},
        existing_inputs=inputs_b,
        lazy=False,
        pending_fields=[],
    )
    trace = load_expansion_trace(outputs)

    assert len(trace) > first_len
    assert any(step.get("operation_type") == "parameter_resolved" for step in trace)
    assert any(step.get("operation_type") == "branch_decision_resolved" for step in trace)
    assert trace[0]["step_number"] == 1
    assert trace[-1]["step_number"] == len(trace)


def test_duplicate_expansion_snapshot_is_not_re_appended() -> None:
    trace = append_expansion_step(
        [],
        operation_type="expansion",
        root_id="wf",
        active_nodes=["A"],
        inputs_fingerprint_text=inputs_fingerprint({"a": 1}),
        lazy=False,
    )
    again = append_expansion_step(
        trace,
        operation_type="expansion",
        root_id="wf",
        active_nodes=["A"],
        inputs_fingerprint_text=inputs_fingerprint({"a": 1}),
        lazy=False,
    )
    assert len(again) == 1


def test_trace_replay_matches_active_nodes() -> None:
    outputs: dict = {}
    active = ["WF-ROOT", "304.1.1-a", "304.1.2-a"]
    record_planning_refresh_trace(
        outputs,
        root_id="pipe_wall_thickness_design",
        preview=_preview(active),
        path_decision=None,
        existing_inputs={"straight_pipe_section": True, "pressure_design_case": "internal_pressure"},
        lazy=False,
    )
    trace = load_expansion_trace(outputs)
    assert replay_active_node_order(trace) == active


def test_trace_steps_convert_to_traversal_events() -> None:
    trace = [
        append_parameter_resolved_step([], field_name="pressure_design_case")[0],
        append_expansion_step(
            [],
            operation_type="expansion",
            root_id="wf",
            active_nodes=["NODE-a"],
            skipped_nodes=[{"node_id": "NODE-x", "reason": "branch not satisfied", "pending": False}],
            pending_fields=["design_pressure"],
            inputs_fingerprint_text="[]",
            lazy=True,
        )[0],
    ]
    events = trace_steps_to_traversal_events(trace)
    types = {event.event_type for event in events}
    assert "parameter_resolved" in types
    assert "node_expanded" in types
    assert "node_marked_not_applicable" in types
    assert "node_deferred" in types


def test_trace_persisted_on_task_outputs_key() -> None:
    outputs: dict = {}
    record_planning_refresh_trace(
        outputs,
        root_id="wf",
        preview=_preview(["A"]),
        path_decision=None,
        existing_inputs={},
        lazy=False,
    )
    assert TRACE_OUTPUT_KEY in outputs
    assert isinstance(outputs[TRACE_OUTPUT_KEY], list)
