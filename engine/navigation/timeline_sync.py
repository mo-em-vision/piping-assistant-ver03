"""Persist timeline row order from graph-driven reveal rules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.navigation.active_input_projection import timeline_revealed_input_ids
from engine.navigation.legacy_timeline_reveal import legacy_timeline_revealed_input_ids
from engine.router import is_supported_planning_workflow
from models.task import Task

if TYPE_CHECKING:
    from engine.reference.standards_reader import StandardsReader


def _task_workflow_id(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")


def sync_timeline_input_order(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> None:
    """Persist timeline row order: keep existing rows, append newly revealed inputs at the bottom."""
    from engine.planner.plan_selection import task_has_stored_engineering_plan

    if task_has_stored_engineering_plan(task) and is_supported_planning_workflow(_task_workflow_id(task)):
        revealed = timeline_revealed_input_ids(task, planning, reader=reader)
    else:
        revealed = legacy_timeline_revealed_input_ids(task, planning, reader=reader)
    task.outputs["timeline_input_order"] = revealed
