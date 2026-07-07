"""UI-friendly task state inspection projections (read-only, no engineering logic)."""

from __future__ import annotations

from typing import Any

from models.task import Task, TaskStatus

_LIFECYCLE_EVENT_LABELS = {
    "beforeEnter": "Node entered (before)",
    "onEnter": "Node discovered",
    "onExecute": "Calculation started",
    "onExit": "Calculation completed",
    "onError": "Warning generated",
}

_EXECUTION_EVENT_LABELS = {
    "node_discovered": "Node discovered",
    "dependency_resolved": "Dependency resolved",
    "input_requested": "Input requested",
    "input_received": "Input received",
    "condition_checked": "Condition checked",
    "decision_created": "Decision made",
    "calculation_started": "Calculation started",
    "calculation_completed": "Calculation completed",
    "warning_created": "Warning generated",
    "report_generated": "Report created",
    "planner_decision": "Planner decision",
}


def build_task_state_views(
    task: Task,
    canonical: dict[str, Any],
    *,
    execution_events: list[Any] | None = None,
    lifecycle_events: list[Any] | None = None,
) -> dict[str, Any]:
    """Build structured inspector views from canonical task state."""
    return {
        "state_summary": _build_state_summary(task, canonical),
        "facts_view": _build_facts_view(canonical),
        "decisions_view": _build_decisions_view(task, canonical),
        "outputs_view": _build_outputs_view(task, canonical),
        "validation_view": _build_validation_view(task, canonical),
        "trace_timeline": _build_trace_timeline(
            execution_events=execution_events or [],
            lifecycle_events=lifecycle_events or [],
        ),
    }


def _build_state_summary(task: Task, canonical: dict[str, Any]) -> dict[str, Any]:
    task_info = canonical.get("task") or {}
    execution = canonical.get("execution") or {}
    progress = canonical.get("progress") or {}
    graph = canonical.get("graph") or {}

    workflow_id = str(task_info.get("workflow_id") or task.outputs.get("workflow") or "")
    selected_root = str(
        task.outputs.get("selected_root")
        or task.outputs.get("graph_root")
        or workflow_id
    )
    status = str(task_info.get("status") or "unknown")
    phase = str(execution.get("phase") or "")

    readiness = "in_progress"
    if status == "completed":
        readiness = "completed"
    elif status == "awaiting_input":
        readiness = "waiting_for_input"
    elif status == "failed":
        readiness = "invalidated"
    elif not progress.get("missing_inputs") and status == "running":
        readiness = "ready"

    return {
        "task_id": task_info.get("id") or task.task_id,
        "task_name": task_info.get("name"),
        "status": status,
        "workflow_id": workflow_id,
        "selected_root": selected_root,
        "current_phase": phase,
        "readiness": readiness,
        "current_blocker": execution.get("current_blocker"),
        "expanded_node_count": len(graph.get("expanded_node_ids") or []),
        "missing_input_count": len(progress.get("missing_inputs") or []),
    }


def _build_facts_view(canonical: dict[str, Any]) -> list[dict[str, Any]]:
    values = canonical.get("values") or {}
    progress = canonical.get("progress") or {}
    missing_inputs = set(progress.get("missing_inputs") or [])
    rows: list[dict[str, Any]] = []

    for field in sorted(values.keys()):
        entry = values.get(field)
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "unknown")
        if field in missing_inputs and status not in {"confirmed", "validated"}:
            status = "missing"
        rows.append(
            {
                "field": field,
                "label": str(entry.get("name") or field.replace("_", " ").title()),
                "symbol": entry.get("symbol"),
                "value": entry.get("display_value") or entry.get("value"),
                "unit": entry.get("unit"),
                "source": entry.get("source") or "unknown",
                "status": status,
                "parameter_node_id": entry.get("parameter_node_id"),
            }
        )

    for field in sorted(missing_inputs):
        if field in values:
            continue
        rows.append(
            {
                "field": field,
                "label": field.replace("_", " ").title(),
                "symbol": None,
                "value": None,
                "unit": None,
                "source": "user_input",
                "status": "missing",
                "parameter_node_id": None,
            }
        )

    return rows


def _build_decisions_view(task: Task, canonical: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    graph = canonical.get("graph") or {}
    progress = canonical.get("progress") or {}

    for decision in (graph.get("selected_branch_decisions") or {}).values():
        if not isinstance(decision, dict):
            continue
        rows.append(
            {
                "kind": "branch_decision",
                "field": decision.get("field"),
                "value": decision.get("value"),
                "selected_node": decision.get("selected_node"),
                "source": "user_input",
                "activated_branch": decision.get("selected_node"),
            }
        )

    for field in progress.get("missing_assumptions") or []:
        rows.append(
            {
                "kind": "assumption",
                "field": field,
                "value": None,
                "selected_node": None,
                "source": "pending",
                "activated_branch": None,
            }
        )

    for name, fact in task.fact_store.active_facts().items():
        if name not in (progress.get("missing_assumptions") or []):
            source = fact.source.source_type.value if fact.source else "unknown"
            if "assumption" in name or source in {"user_input", "default_confirmed"}:
                if any(row.get("field") == name for row in rows):
                    continue
                rows.append(
                    {
                        "kind": "assumption",
                        "field": name,
                        "value": fact.value,
                        "selected_node": fact.parameter,
                        "source": source,
                        "activated_branch": None,
                    }
                )

    return rows


def _build_outputs_view(task: Task, canonical: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    values = canonical.get("values") or {}
    progress = canonical.get("progress") or {}
    graph = canonical.get("graph") or {}
    resolved_nodes = set(graph.get("resolved_node_ids") or [])

    derived_sources = {"derived", "lookup", "equation", "calculation", "table_lookup"}

    for field, entry in sorted(values.items()):
        if not isinstance(entry, dict):
            continue
        source = str(entry.get("source") or "")
        if source not in derived_sources and field not in {
            "required_thickness",
            "minimum_required_thickness",
            "mawp",
            "allowable_stress",
        }:
            continue
        status = "produced" if entry.get("status") in {"confirmed", "validated"} else "pending"
        rows.append(
            {
                "field": field,
                "label": str(entry.get("name") or field.replace("_", " ").title()),
                "value": entry.get("display_value") or entry.get("value"),
                "unit": entry.get("unit"),
                "producing_node": entry.get("parameter_node_id"),
                "status": status,
                "warnings": [],
            }
        )

    for step in progress.get("steps") or []:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "")
        if step.get("status") != "done":
            continue
        if any(row.get("field") == step_id for row in rows):
            continue
        rows.append(
            {
                "field": step_id,
                "label": str(step.get("title") or step_id.replace("_", " ").title()),
                "value": step.get("value"),
                "unit": step.get("unit"),
                "producing_node": step.get("provenance_id"),
                "status": "produced",
                "warnings": [],
            }
        )

    for warning in task.warnings:
        if rows:
            rows[-1]["warnings"] = list(rows[-1].get("warnings") or []) + [warning]

    if not rows and resolved_nodes:
        for node_id in resolved_nodes:
            rows.append(
                {
                    "field": node_id,
                    "label": node_id,
                    "value": None,
                    "unit": None,
                    "producing_node": node_id,
                    "status": "produced",
                    "warnings": [],
                }
            )

    return rows


def _build_validation_view(task: Task, canonical: dict[str, Any]) -> dict[str, Any]:
    debug = canonical.get("debug") or {}
    execution = canonical.get("execution") or {}
    blocker = execution.get("current_blocker") or {}

    warnings = list(debug.get("warnings") or [])
    warnings.extend(task.warnings)

    errors: list[str] = []
    if task.status == TaskStatus.INVALIDATED:
        errors.append(blocker.get("message") or "Task invalidated")
    if blocker.get("type") == "validation_error":
        errors.append(str(blocker.get("message") or "Validation error"))

    conflicts: list[dict[str, Any]] = []
    for field, entry in (canonical.get("values") or {}).items():
        if isinstance(entry, dict) and entry.get("status") == "invalidated":
            conflicts.append({"field": field, "reason": "Value invalidated"})

    return {
        "status": "failed" if errors else ("warning" if warnings else "ok"),
        "errors": errors,
        "warnings": warnings,
        "overrides": [],
        "conflicts": conflicts,
        "affected_nodes": list((canonical.get("graph") or {}).get("active_node_ids") or []),
    }


def _build_trace_timeline(
    *,
    execution_events: list[Any],
    lifecycle_events: list[Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for index, item in enumerate(execution_events):
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("event") or "")
        label = _EXECUTION_EVENT_LABELS.get(event_type, event_type.replace("_", " "))
        message = _format_execution_event_message(item)
        rows.append(
            {
                "order": index + 1,
                "event_type": event_type,
                "label": label,
                "node_id": item.get("node"),
                "message": message,
                "timestamp": item.get("timestamp"),
                "source": "execution",
            }
        )

    base_order = len(rows)
    for index, item in enumerate(lifecycle_events):
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("event") or "")
        label = _LIFECYCLE_EVENT_LABELS.get(event_type, event_type)
        message = str(item.get("message") or "")
        rows.append(
            {
                "order": base_order + index + 1,
                "event_type": event_type,
                "label": label,
                "node_id": item.get("node_id"),
                "message": message,
                "timestamp": item.get("timestamp"),
                "source": "lifecycle",
            }
        )

    return rows


def _format_execution_event_message(item: dict[str, Any]) -> str:
    parts: list[str] = []
    if item.get("decision"):
        parts.append(f"Decision: {item['decision']}")
    if item.get("result") is not None:
        parts.append(f"Result: {item['result']}")
    payload = item.get("payload")
    if isinstance(payload, dict) and payload.get("field"):
        parts.append(f"Field: {payload['field']}")
    if parts:
        return " · ".join(parts)
    node = item.get("node")
    if node:
        return f"Node: {node}"
    return ""
