"""Migrate legacy task payloads to ExecutionContext v4."""

from __future__ import annotations

from typing import Any

from engine.state.fact_migration import facts_from_legacy_inputs
from models.execution_context import (
    ExecutionContext,
    InputConflict,
    execution_context_for_task,
    execution_context_from_dict,
    execution_context_to_dict,
)
from models.fact_store import FactStore
from models.goal_store import GoalStore
from models.task import Task, TaskStatus


def migrate_task_to_v4(data: dict[str, Any]) -> dict[str, Any]:
    """Return task dict with execution_context for payload_version 4."""
    version = int(data.get("payload_version", 3))
    if version >= 4 and data.get("execution_context"):
        return data

    task_id = str(data["task_id"])
    status = TaskStatus(data.get("status", TaskStatus.ACTIVE.value))
    workflow_id = str(data.get("outputs", {}).get("workflow") or "")

    if data.get("execution_context"):
        ctx = execution_context_from_dict(data["execution_context"])
    else:
        ctx = execution_context_for_task(
            task_id,
            workflow_id=workflow_id or None,
            status=status,
        )
        fact_store_data = data.get("fact_store")
        if fact_store_data:
            ctx.fact_store = FactStore.from_dict(fact_store_data)
        elif data.get("inputs"):
            legacy_inputs = _legacy_inputs_from_dict(data.get("inputs") or {})
            if legacy_inputs:
                ctx.fact_store = facts_from_legacy_inputs(
                    legacy_inputs,
                    task_id=task_id,
                    workflow_id=workflow_id or None,
                )
        ctx.goal_store = GoalStore.from_dict(data.get("goal_store"))
        ctx.warnings = list(data.get("warnings") or [])
        ctx.conflicts = [
            InputConflict(**item) if isinstance(item, dict) else item
            for item in (data.get("conflicts") or [])
        ]

    _assign_execution_context_ids(ctx)

    migrated = {
        "task_id": task_id,
        "active_nodes": list(data.get("active_nodes", [])),
        "execution_context": execution_context_to_dict(ctx),
        "outputs": dict(data.get("outputs", {})),
        "parameter_registry": dict(data.get("parameter_registry") or {}),
        "payload_version": 4,
    }
    return migrated


def wrap_legacy_task(task: Task) -> Task:
    """Ensure task has execution_context populated from legacy fields if needed."""
    from engine.state.goal_migration import migrate_task_goals_from_outputs

    if task.payload_version >= 4 and task.execution_context.id:
        migrate_task_goals_from_outputs(task)
        return task
    return task


def _assign_execution_context_ids(ctx: ExecutionContext) -> None:
    for fact in ctx.fact_store.facts.values():
        if fact.provenance.execution_context_id is None:
            fact.provenance.execution_context_id = ctx.id
    for goal in ctx.goal_store.goals.values():
        if goal.provenance.execution_context_id is None:
            goal.provenance.execution_context_id = ctx.id


def _legacy_inputs_from_dict(raw: dict[str, Any]) -> dict[str, Any]:
    from models.input import EngineeringInput, InputSource, InputStatus

    result: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        result[key] = EngineeringInput(
            input_id=value.get("input_id", key),
            value=value["value"],
            unit=value.get("unit", "dimensionless"),
            source=InputSource(value["source"]),
            status=InputStatus(value.get("status", InputStatus.PENDING.value)),
            default=value.get("default"),
            requires_confirmation=bool(value.get("requires_confirmation", False)),
            uncertainty=value.get("uncertainty"),
            original_value=value.get("original_value"),
            original_unit=value.get("original_unit"),
        )
    return result
