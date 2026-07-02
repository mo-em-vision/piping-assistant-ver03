"""Test helpers for runtime Goal nodes."""

from __future__ import annotations

from typing import Any

from engine.state.execution_context_sync import refresh_execution_context_for_task
from engine.state.goal_migration import goals_from_planning_summary
from models.task import Task


def apply_planning_to_goals(
    task: Task,
    planning: dict[str, Any],
    *,
    workflow_id: str | None = None,
) -> Task:
    """Attach a goal tree derived from a legacy planning_summary-shaped dict."""
    wf = workflow_id or str(task.outputs.get("workflow") or planning.get("intent") or "")
    task.execution_context.goal_store = goals_from_planning_summary(
        planning,
        task_id=task.task_id,
        workflow_id=wf or None,
    )
    if planning.get("selected_nodes"):
        task.outputs["selected_nodes"] = list(planning["selected_nodes"])
    if planning.get("active_definition_node"):
        task.outputs["active_definition_node"] = planning["active_definition_node"]
    if planning.get("path_decision"):
        task.outputs["path_decision"] = planning["path_decision"]
    if planning.get("graph_input_order"):
        task.outputs["graph_input_order"] = planning["graph_input_order"]
    if planning.get("graph_step_titles"):
        task.outputs["graph_step_titles"] = planning["graph_step_titles"]
    refresh_execution_context_for_task(task, workflow_id=wf or None)
    return task


def task_with_planning(
    task: Task,
    planning: dict[str, Any],
    *,
    workflow_id: str | None = None,
) -> Task:
    """Set workflow outputs and build goals from planning dict (test convenience)."""
    if workflow_id:
        task.outputs["workflow"] = workflow_id
        task.outputs["selected_root"] = workflow_id
    return apply_planning_to_goals(task, planning, workflow_id=workflow_id)
