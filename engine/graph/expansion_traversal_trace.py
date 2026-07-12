"""Append-only expansion traversal trace for graph visualizer replay.

Developer/debug data only — not rendered as center-panel user output.
"""

from __future__ import annotations

import json
from typing import Any

from engine.graph.traversal_reasons import (
    EXCLUSION_REASON_BRANCH_CONDITION_NOT_SATISFIED,
    EXCLUSION_REASON_NOT_APPLICABLE,
    QUEUE_REASON_BRANCH_CONDITION_PENDING,
    QUEUE_REASON_WAITING_FOR_DEPENDENCY,
    QUEUE_REASON_WAITING_FOR_USER_INPUT,
    normalize_exclusion_reason,
    normalize_queue_reason,
)
from models.engineering_plan import TraversalEvent

TRACE_OUTPUT_KEY = "_expansion_traversal_trace"


def load_expansion_trace(outputs: dict[str, Any]) -> list[dict[str, Any]]:
    raw = outputs.get(TRACE_OUTPUT_KEY)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def store_expansion_trace(outputs: dict[str, Any], trace: list[dict[str, Any]]) -> None:
    outputs[TRACE_OUTPUT_KEY] = list(trace)


def inputs_fingerprint(inputs: dict[str, Any]) -> str:
    """Stable fingerprint of resolved input field keys and scalar values."""
    pairs: list[tuple[str, str]] = []
    for key in sorted(inputs.keys()):
        value = inputs[key]
        if hasattr(value, "value"):
            scalar = getattr(value, "value", value)
        elif isinstance(value, dict):
            scalar = value.get("value", value)
        else:
            scalar = value
        pairs.append((str(key), str(scalar)))
    return json.dumps(pairs, sort_keys=True, separators=(",", ":"))


def _next_step_number(trace: list[dict[str, Any]]) -> int:
    if not trace:
        return 1
    return int(trace[-1].get("step_number", len(trace))) + 1


def _skipped_to_excluded(skipped_nodes: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in skipped_nodes:
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id") or "")
        if not node_id:
            continue
        reason_text = str(item.get("reason") or "")
        if item.get("pending"):
            continue
        rows.append(
            {
                "node_id": node_id,
                "exclusion_reason": normalize_exclusion_reason(reason_text),
                "detail": reason_text,
            }
        )
    return rows


def _pending_to_queued(
    pending_fields: list[str],
    *,
    lazy: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field_name in pending_fields:
        rows.append(
            {
                "node_id": field_name,
                "queue_reason": (
                    QUEUE_REASON_BRANCH_CONDITION_PENDING
                    if lazy
                    else QUEUE_REASON_WAITING_FOR_USER_INPUT
                ),
                "waiting_on": [field_name],
            }
        )
    return rows


def append_expansion_step(
    trace: list[dict[str, Any]],
    *,
    operation_type: str,
    root_id: str,
    active_nodes: list[str],
    skipped_nodes: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
    pending_fields: list[str] | None = None,
    path_decision: dict[str, str] | None = None,
    inputs_fingerprint_text: str,
    lazy: bool = False,
    edges_taken: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Append a new expansion step when the planning fingerprint changes."""
    skipped_nodes = list(skipped_nodes or [])
    pending_fields = list(pending_fields or [])
    excluded = _skipped_to_excluded(skipped_nodes)
    queued = _pending_to_queued(pending_fields, lazy=lazy)

    step_payload = {
        "operation_type": operation_type,
        "root_id": root_id,
        "active_nodes": list(active_nodes),
        "excluded_nodes": excluded,
        "queued_nodes": queued,
        "path_decision": dict(path_decision or {}),
        "inputs_fingerprint": inputs_fingerprint_text,
        "lazy": lazy,
        "edges_taken": list(edges_taken or []),
    }

    if trace:
        last = trace[-1]
        if (
            last.get("operation_type") == operation_type
            and last.get("inputs_fingerprint") == inputs_fingerprint_text
            and last.get("active_nodes") == step_payload["active_nodes"]
            and last.get("excluded_nodes") == excluded
            and last.get("queued_nodes") == queued
            and last.get("path_decision") == step_payload["path_decision"]
        ):
            return trace

    step = {
        "step_number": _next_step_number(trace),
        **step_payload,
    }
    return [*trace, step]


def append_parameter_resolved_step(
    trace: list[dict[str, Any]],
    *,
    field_name: str,
    node_id: str | None = None,
) -> list[dict[str, Any]]:
    """Append a user-input resolution event (always recorded)."""
    if trace:
        last = trace[-1]
        if (
            last.get("operation_type") == "parameter_resolved"
            and last.get("field_name") == field_name
        ):
            return trace
    step = {
        "step_number": _next_step_number(trace),
        "operation_type": "parameter_resolved",
        "field_name": field_name,
        "node_id": node_id,
    }
    return [*trace, step]


def append_branch_decision_step(
    trace: list[dict[str, Any]],
    *,
    field_name: str,
    value: str,
    selected_node: str | None,
) -> list[dict[str, Any]]:
    """Append a branch resolution event."""
    if trace:
        last = trace[-1]
        if (
            last.get("operation_type") == "branch_decision_resolved"
            and last.get("field_name") == field_name
            and last.get("value") == value
            and last.get("selected_node") == selected_node
        ):
            return trace
    step = {
        "step_number": _next_step_number(trace),
        "operation_type": "branch_decision_resolved",
        "field_name": field_name,
        "value": value,
        "selected_node": selected_node,
    }
    return [*trace, step]


def _resolved_field_keys(inputs: dict[str, Any]) -> set[str]:
    return {str(key) for key in inputs.keys() if str(key).strip()}


def _fingerprint_field_keys(fingerprint: str) -> set[str]:
    try:
        pairs = json.loads(fingerprint)
    except (TypeError, json.JSONDecodeError):
        return set()
    if not isinstance(pairs, list):
        return set()
    return {str(pair[0]) for pair in pairs if isinstance(pair, list) and pair}


def record_planning_refresh_trace(
    task_outputs: dict[str, Any],
    *,
    root_id: str,
    preview: Any,
    path_decision: dict[str, str] | None,
    existing_inputs: dict[str, Any],
    lazy: bool,
    pending_fields: list[str] | None = None,
) -> None:
    """Update task outputs with append-only expansion trace for this refresh."""
    trace = load_expansion_trace(task_outputs)
    fingerprint = inputs_fingerprint(existing_inputs)
    current_keys = _resolved_field_keys(existing_inputs)
    previous_keys: set[str] = set()
    if trace:
        previous_keys = _fingerprint_field_keys(str(trace[-1].get("inputs_fingerprint") or ""))
    for field_name in sorted(current_keys - previous_keys):
        trace = append_parameter_resolved_step(trace, field_name=field_name)

    active_nodes = list(getattr(preview, "execution_order", ()) or [])
    skipped = getattr(preview, "skipped_nodes", ()) or ()

    trace = append_expansion_step(
        trace,
        operation_type="expansion",
        root_id=root_id,
        active_nodes=active_nodes,
        skipped_nodes=skipped,
        pending_fields=pending_fields,
        path_decision=path_decision,
        inputs_fingerprint_text=fingerprint,
        lazy=lazy,
    )

    if isinstance(path_decision, dict):
        field_name = str(path_decision.get("field") or path_decision.get("parameter") or "")
        value = str(path_decision.get("value") or path_decision.get("choice") or "")
        selected = path_decision.get("selected_node")
        if field_name and value:
            trace = append_branch_decision_step(
                trace,
                field_name=field_name,
                value=value,
                selected_node=str(selected) if selected else None,
            )

    store_expansion_trace(task_outputs, trace)


def trace_steps_to_traversal_events(trace: list[dict[str, Any]]) -> list[TraversalEvent]:
    """Convert stored expansion trace steps into planner traversal events."""
    events: list[TraversalEvent] = []
    order = 0
    for step in trace:
        op = str(step.get("operation_type") or "")
        if op == "expansion":
            for node_id in step.get("active_nodes") or []:
                order += 1
                events.append(
                    TraversalEvent(
                        order=order,
                        event_type="node_expanded",
                        node_id=str(node_id),
                        message=f"Expansion step {step.get('step_number')}: active node {node_id}.",
                    )
                )
            for item in step.get("excluded_nodes") or []:
                if not isinstance(item, dict):
                    continue
                node_id = item.get("node_id")
                if not node_id:
                    continue
                order += 1
                reason = item.get("exclusion_reason") or EXCLUSION_REASON_NOT_APPLICABLE
                events.append(
                    TraversalEvent(
                        order=order,
                        event_type="node_marked_not_applicable",
                        node_id=str(node_id),
                        message=f"Excluded ({reason}): {item.get('detail', node_id)}",
                    )
                )
            for item in step.get("queued_nodes") or []:
                if not isinstance(item, dict):
                    continue
                node_id = item.get("node_id")
                if not node_id:
                    continue
                order += 1
                reason = item.get("queue_reason") or QUEUE_REASON_WAITING_FOR_DEPENDENCY
                events.append(
                    TraversalEvent(
                        order=order,
                        event_type="node_deferred",
                        node_id=str(node_id),
                        message=f"Queued ({reason}).",
                    )
                )
            for edge in step.get("edges_taken") or []:
                if not isinstance(edge, dict):
                    continue
                order += 1
                events.append(
                    TraversalEvent(
                        order=order,
                        event_type="edge_taken",
                        edge_id=str(edge.get("edge_id") or edge.get("to_id") or ""),
                        message=str(edge.get("reason") or "edge taken"),
                    )
                )
        elif op == "parameter_resolved":
            order += 1
            events.append(
                TraversalEvent(
                    order=order,
                    event_type="parameter_resolved",
                    node_id=step.get("node_id"),
                    message=f"User input resolved for {step.get('field_name')}.",
                )
            )
        elif op == "branch_decision_resolved":
            order += 1
            events.append(
                TraversalEvent(
                    order=order,
                    event_type="branch_decision_resolved",
                    node_id=step.get("selected_node"),
                    message=(
                        f"Branch {step.get('field_name')} resolved to {step.get('value')!r} "
                        f"via node {step.get('selected_node')}."
                    ),
                )
            )
    return events


def replay_active_node_order(trace: list[dict[str, Any]]) -> list[str]:
    """Return node ids in expansion order from the last expansion step (for replay tests)."""
    for step in reversed(trace):
        if step.get("operation_type") == "expansion":
            return [str(node_id) for node_id in step.get("active_nodes") or []]
    return []
