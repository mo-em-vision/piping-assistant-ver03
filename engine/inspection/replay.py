"""Execution replay frame builder."""

from __future__ import annotations

from typing import Any

from engine.inspection.models import ExecutionTraceStep, PlannerDecision, ReplayFrame
from models.workflow_state import WorkflowState


def build_replay_frames(
    trace_steps: list[ExecutionTraceStep],
    workflow_state: WorkflowState,
    outputs: dict[str, Any],
    *,
    planner_decisions: dict[str, PlannerDecision] | None = None,
) -> list[ReplayFrame]:
    """Build replay frames from execution trace and workflow state."""
    if not trace_steps:
        return [
            ReplayFrame(
                frame_index=0,
                step_index=None,
                active_node=workflow_state.current_node,
                visited_nodes=list(workflow_state.visited_nodes),
                pending_nodes=[],
                variables=dict(workflow_state.variable_values),
                outputs=_user_outputs(outputs),
                planner_state={
                    "planning_summary": outputs.get("planning_summary") or {},
                },
                context={
                    "current_node": workflow_state.current_node,
                    "warnings": list(workflow_state.warnings),
                },
            )
        ]

    frames: list[ReplayFrame] = []
    visited: list[str] = []
    pending = [step.node_id for step in trace_steps]
    accumulated_outputs = _user_outputs(outputs)

    for frame_index, step in enumerate(trace_steps):
        if step.node_id in pending:
            pending.remove(step.node_id)
        if step.node_id not in visited:
            visited.append(step.node_id)

        decision = (planner_decisions or {}).get(step.node_id)
        planner_state: dict[str, Any] = {
            "planning_summary": outputs.get("planning_summary") or {},
        }
        if decision is not None:
            planner_state["decision"] = decision.to_dict()

        frames.append(
            ReplayFrame(
                frame_index=frame_index,
                step_index=step.step_index,
                active_node=step.node_id,
                visited_nodes=list(visited),
                pending_nodes=list(pending),
                variables=dict(workflow_state.variable_values),
                outputs={**accumulated_outputs, **step.outputs},
                planner_state=planner_state,
                context={
                    "node_id": step.node_id,
                    "node_type": step.node_type,
                    "status": step.status,
                    "selection_reason": step.selection_reason,
                    "duration_ms": step.duration_ms,
                },
            )
        )

    return frames


def build_replay_snapshot(frames: list[ReplayFrame]) -> dict[str, Any]:
    """Immutable replay snapshot for persistence."""
    return {
        "frame_count": len(frames),
        "frames": [frame.to_dict() for frame in frames],
    }


def _user_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    skip_prefixes = ("_",)
    skip_keys = {
        "workflow",
        "graph_root",
        "graph_version",
        "planning_summary",
        "selected_root",
    }
    result: dict[str, Any] = {}
    for key, value in outputs.items():
        if key in skip_keys or key.startswith(skip_prefixes):
            continue
        result[key] = value
    return result
