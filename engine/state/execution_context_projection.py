"""Build API-facing execution context summaries."""

from __future__ import annotations

from typing import Any

from models.execution_context import ExecutionContext, execution_context_to_dict
from models.task import Task


def execution_context_summary(task: Task) -> dict[str, Any]:
    ctx = task.execution_context
    return {
        "id": ctx.id,
        "type": ctx.type,
        "task_id": ctx.task_id,
        "workflow_id": ctx.workflow_id,
        "project_id": ctx.project_id,
        "status": ctx.status.value,
        "authority_context_id": ctx.authority_context_id,
        "active_goals": list(ctx.active_goals),
        "facts": {
            "active_count": len(ctx.facts_index.active),
            "superseded_count": len(ctx.facts_index.superseded),
            "conflicting_count": len(ctx.facts_index.conflicting),
        },
        "state": {
            "current_phase": ctx.state.current_phase,
            "blocked_by": list(ctx.state.blocked_by),
            "ready_goals": list(ctx.state.ready_goals),
            "blocked_goals": list(ctx.state.blocked_goals),
            "completed_goals": list(ctx.state.completed_goals),
        },
        "decisions_count": len(ctx.decisions),
        "assumptions_count": len(ctx.assumptions),
        "validation_status": ctx.validation.status,
        "warnings_count": len(ctx.warnings),
        "conflicts_count": len(ctx.conflicts),
        "execution_trace_events": len(ctx.execution_trace.events),
    }


def execution_context_full(task: Task) -> dict[str, Any]:
    return execution_context_to_dict(task.execution_context)
