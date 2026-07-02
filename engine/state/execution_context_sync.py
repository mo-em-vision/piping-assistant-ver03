"""Recompute materialized ExecutionContext state from facts and goals."""

from __future__ import annotations

from datetime import datetime, timezone

from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import (
    current_phase,
    missing_input_keys,
)
from engine.state.goal_satisfaction import refresh_goal_satisfaction
from models.execution_context import ExecutionContext, ExecutionMetadata
from models.fact import ValidationStatus
from models.goal import SatisfactionStatus
from models.task import Task


def ensure_authority_context(
    ctx: ExecutionContext,
    reader: StandardsReader | None = None,
    workflow_id: str | None = None,
    *,
    task: Task | None = None,
) -> None:
    if task is not None:
        from engine.state.authority_context_sync import ensure_authority_context_for_task

        ensure_authority_context_for_task(task, reader=reader, workflow_id=workflow_id)
        return
    if ctx.authority_context_id:
        return
    wf = workflow_id or ctx.workflow_id
    if not wf:
        return
    standard = "asme-b31.3"
    if reader is not None:
        standard = str(getattr(reader, "standard", standard) or standard).replace("_", "-")
    ctx.authority_context_id = f"AUTHCTX-{standard}"


def refresh_execution_context(
    ctx: ExecutionContext,
    *,
    workflow_id: str | None = None,
    reader: StandardsReader | None = None,
) -> None:
    """Refresh facts index, goal state, and active_goals on the context."""
    if workflow_id:
        ctx.workflow_id = workflow_id

    refresh_goal_satisfaction_ctx(ctx)

    active_ids: list[str] = []
    superseded_ids: list[str] = []
    conflicting_ids: list[str] = []
    for fact in ctx.fact_store.facts.values():
        if fact.supersession.active:
            active_ids.append(fact.id)
        elif fact.validation.status == ValidationStatus.SUPERSEDED:
            superseded_ids.append(fact.id)
        if fact.validation.status == ValidationStatus.CONFLICTING:
            conflicting_ids.append(fact.id)

    ctx.facts_index.active = sorted(set(active_ids))
    ctx.facts_index.superseded = sorted(set(superseded_ids))
    ctx.facts_index.conflicting = sorted(set(conflicting_ids))

    ctx.state.current_phase = current_phase_ctx(ctx)
    ctx.state.blocked_by = [
        f"PARAM-{key.replace('_', '-')}" for key in missing_input_keys_ctx(ctx)
    ]

    ready: list[str] = []
    blocked: list[str] = []
    completed: list[str] = []
    for goal in ctx.goal_store.goals.values():
        if goal.satisfaction.status == SatisfactionStatus.SATISFIED:
            completed.append(goal.id)
        elif goal.satisfaction.status == SatisfactionStatus.BLOCKED:
            blocked.append(goal.id)
        elif goal.satisfaction.status == SatisfactionStatus.READY:
            ready.append(goal.id)

    ctx.state.ready_goals = ready
    ctx.state.blocked_goals = blocked
    ctx.state.completed_goals = completed
    ctx.active_goals = [g.id for g in ctx.goal_store.roots()]

    if ctx.warnings:
        ctx.validation.warnings = list(ctx.warnings)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if ctx.metadata.created is None:
        ctx.metadata.created = now
    ctx.metadata.modified = now

    ensure_authority_context(ctx, reader, workflow_id)


def refresh_execution_context_for_task(
    task: Task,
    *,
    workflow_id: str | None = None,
    reader: StandardsReader | None = None,
) -> None:
    wf = workflow_id or str(task.outputs.get("workflow") or task.execution_context.workflow_id or "")
    if wf:
        task.execution_context.workflow_id = wf
    refresh_execution_context(task.execution_context, workflow_id=wf or None, reader=reader)
    from engine.state.authority_context_sync import ensure_authority_context_for_task

    ensure_authority_context_for_task(task, reader=reader, workflow_id=wf or None)
    _sync_trace_event_refs(task)


def _sync_trace_event_refs(task: Task) -> None:
    trace = task.outputs.get("_execution_trace")
    if not isinstance(trace, list):
        return
    events: list[str] = []
    for index, step in enumerate(trace):
        if isinstance(step, dict):
            node_id = step.get("node_id") or step.get("id") or f"step-{index}"
            events.append(f"EVENT-{node_id}-{index}")
    task.execution_context.execution_trace.events = events


def refresh_goal_satisfaction_ctx(ctx: ExecutionContext) -> None:
    """Run goal satisfaction against context stores."""
    from models.task import Task

    shim = Task(task_id=ctx.task_id, execution_context=ctx)
    refresh_goal_satisfaction(shim)


def current_phase_ctx(ctx: ExecutionContext) -> str:
    from models.task import Task

    return current_phase(Task(task_id=ctx.task_id, execution_context=ctx))


def missing_input_keys_ctx(ctx: ExecutionContext) -> list[str]:
    from models.task import Task

    return missing_input_keys(Task(task_id=ctx.task_id, execution_context=ctx))
