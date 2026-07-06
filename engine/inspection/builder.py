"""Assemble the full developer inspection payload."""

from __future__ import annotations

from typing import Any

from api.json_encoding import json_safe
from engine.inspection.operation_tracker import track_operation
from engine.inspection.provenance import build_provenance_index
from engine.inspection.integrity import run_integrity_checks
from engine.inspection.models import ExecutionTraceStep
from engine.inspection.planner_decisions import (
    planner_decisions_from_task_outputs,
)
from engine.inspection.replay import build_replay_frames, build_replay_snapshot
from engine.inspection.trace import build_execution_trace
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from engine.state.authority_context_projection import authority_context_full
from engine.state.execution_context_projection import execution_context_full
from engine.state.goal_projection import goals_to_api_dict, planning_projection
from engine.state.task_state_canonical import (
    build_canonical_task_state,
    build_task_inspector_summary,
)
from engine.planner.plan_inspector import engineering_plan_view_for_task
from engine.state.workflow_state import build_workflow_state
from models.task import Task


def build_inspection_payload(
    task: Task,
    *,
    manager: TaskStateManager,
    reader: StandardsReader | None = None,
) -> dict[str, Any]:
    """Build the consolidated inspection API response."""
    with track_operation(
        "build_inspection_payload",
        category="inspection",
        task_id=task.task_id,
    ):
        return _build_inspection_payload_impl(task, manager=manager, reader=reader)


def _build_inspection_payload_impl(
    task: Task,
    *,
    manager: TaskStateManager,
    reader: StandardsReader | None = None,
) -> dict[str, Any]:
    outputs = dict(task.outputs)
    workflow_id = str(
        outputs.get("workflow")
        or outputs.get("graph_root")
        or outputs.get("selected_root")
        or ""
    )

    trace_steps = build_execution_trace(outputs, reader=reader, workflow_id=workflow_id)
    planner_decisions = planner_decisions_from_task_outputs(outputs)
    provenance_index = build_provenance_index(task, reader) if reader else []
    provenance_warnings = [
        f"Block {record.display_id} has no provenance"
        for record in provenance_index
        if record.missing
    ]
    workflow_state = build_workflow_state(
        task,
        step_progress=manager.list_step_progress(task.task_id),
        reader=reader,
    )

    replay_frames = build_replay_frames(
        trace_steps,
        workflow_state,
        outputs,
        planner_decisions=planner_decisions,
    )
    replay_snapshot = outputs.get("_replay_snapshot")
    if not isinstance(replay_snapshot, dict):
        replay_snapshot = build_replay_snapshot(replay_frames)

    performance = _performance_summary(trace_steps)
    integrity = run_integrity_checks(reader) if reader else []

    canonical = build_canonical_task_state(
        task,
        manager,
        reader=reader,
    )
    inspector_summary = build_task_inspector_summary(canonical)

    return json_safe(
        {
            "task_id": task.task_id,
            "workflow_id": workflow_id,
            "execution_trace": [step.to_dict() for step in trace_steps],
            "planner_decisions": {
                node_id: decision.to_dict() for node_id, decision in planner_decisions.items()
            },
            "goals": goals_to_api_dict(task),
            "execution_context": execution_context_full(task),
            "authority_context": authority_context_full(task),
            "planning_summary": planning_projection(task),
            "engineering_plan": engineering_plan_view_for_task(task),
            "planner_inspector_summary": task.outputs.get("planner_inspector_summary"),
            "provenance_index": [record.to_dict() for record in provenance_index],
            "provenance_warnings": provenance_warnings or list(outputs.get("_provenance_warnings") or []),
            "workflow_state": _workflow_state_dict(workflow_state),
            "inspector_summary": inspector_summary,
            "canonical_task_state": canonical,
            "execution_events": outputs.get("_execution_events") or [],
            "lifecycle_events": outputs.get("_lifecycle_events") or [],
            "replay_frames": [frame.to_dict() for frame in replay_frames],
            "replay_snapshot": replay_snapshot,
            "integrity_checks": [check.to_dict() for check in integrity],
            "performance": performance,
            "breakpoint": outputs.get("_inspection_breakpoint") or {"paused": False},
        }
    )


def _workflow_state_dict(workflow_state: Any) -> dict[str, Any]:
    from dataclasses import asdict

    return json_safe(asdict(workflow_state))


def _performance_summary(trace_steps: list[ExecutionTraceStep]) -> dict[str, Any]:
    durations = [step.duration_ms for step in trace_steps if step.duration_ms is not None]
    total_ms = sum(durations) if durations else 0.0
    by_node = {
        step.node_id: step.duration_ms
        for step in trace_steps
        if step.duration_ms is not None
    }
    return {
        "total_duration_ms": round(total_ms, 3),
        "step_count": len(trace_steps),
        "by_node_ms": by_node,
    }
