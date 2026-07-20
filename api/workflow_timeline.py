"""Dynamic workflow timeline and revealed parameter ordering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.graph.graph_timeline import graph_input_step_order, graph_step_titles
from engine.navigation import (
    HIDDEN_TIMELINE_INPUTS,
    collect_all_missing,
    collection_step_order,
    composer_parameter_id,
    composer_parameter_ids,
    hidden_timeline_inputs,
    step_applies_for_timeline,
    submittable_parameter_ids,
    sync_timeline_input_order,
    timeline_revealed_input_ids,
    timeline_step_id_for_parameter,
    uses_inside_diameter_path,
    uses_planner_input_projection,
)
from engine.navigation.timeline_row_ids import timeline_row_id
from engine.reference.parameter_keys import api_parameter_id
from engine.reports.block_renderer import has_timeline_input_label, input_label_for_timeline
from engine.router import is_supported_planning_workflow
from models.fact import Fact, FactClass, ValidationStatus, fact_scalar_value
from models.task import Task

if TYPE_CHECKING:
    from engine.reference.standards_reader import StandardsReader

# Backward-compatible private aliases for API modules that import underscore names.
_HIDDEN_TIMELINE_INPUTS = HIDDEN_TIMELINE_INPUTS
_pipe_wall_uses_inside_diameter = uses_inside_diameter_path
_pipe_wall_step_applies = step_applies_for_timeline
_hidden_timeline_inputs = hidden_timeline_inputs
_step_applies_for_timeline = step_applies_for_timeline


def _task_workflow_id(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")


def parameter_collection_index(
    task: Task,
    parameter_id: str,
    *,
    reader: StandardsReader | None = None,
) -> int | None:
    planning = task.outputs.get("engineering_plan_view") or {}
    step_order = collection_step_order(task, planning, reader=reader)
    canonical = api_parameter_id(parameter_id)
    for index, step_id in enumerate(step_order):
        if api_parameter_id(step_id) == canonical:
            return index
    return None


def _resolve_graph_step_titles(
    task: Task,
    planning: dict[str, Any] | None,
    *,
    reader: StandardsReader | None,
) -> dict[str, str]:
    titles = dict((planning or {}).get("graph_step_titles") or {})
    if titles or reader is None:
        return titles
    graph = task.outputs.get("graph_root") or task.outputs.get("selected_root") or task.outputs.get("workflow")
    if not graph:
        return titles
    from engine.graph.graph_engine import GraphEngine, normalize_root_id

    preview = GraphEngine().build_plan(
        task_id=task.task_id,
        root_id=normalize_root_id(str(graph)),
        inputs=dict(task.fact_store.active_facts()),
        reader=reader,
    )
    return graph_step_titles(reader, preview)


def _step_title_from_graph(
    task: Task,
    step_id: str,
    planning: dict[str, Any] | None,
    *,
    reader: StandardsReader | None,
) -> str:
    _BUILTIN_STEP_TITLES = {
        "thickness": "Thickness",
        "mawp": "MAWP",
        "report": "Report",
    }
    if step_id in _BUILTIN_STEP_TITLES:
        return _BUILTIN_STEP_TITLES[step_id]
    canonical_id = timeline_row_id(api_parameter_id(step_id))
    if has_timeline_input_label(canonical_id):
        return input_label_for_timeline(canonical_id)
    titles = _resolve_graph_step_titles(task, planning, reader=reader)
    if canonical_id in titles:
        return titles[canonical_id]
    if step_id in titles:
        return titles[step_id]
    return input_label_for_timeline(canonical_id)


def revealed_input_ids(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    if uses_planner_input_projection(task):
        return timeline_revealed_input_ids(task, planning, reader=reader)
    from engine.navigation.legacy_timeline_reveal import legacy_timeline_revealed_input_ids

    return legacy_timeline_revealed_input_ids(task, planning, reader=reader)


def revealed_pipe_wall_input_ids(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    return revealed_input_ids(task, planning, reader=reader)


def revealed_mawp_input_ids(
    task: Task,
    planning: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    return revealed_input_ids(task, planning, reader=reader)


def workflow_step_title(
    task: Task,
    step_id: str,
    planning: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> str:
    return _step_title_from_graph(task, step_id, planning, reader=reader)


def pipe_wall_step_title(
    step_id: str,
    planning: dict[str, Any] | None = None,
    *,
    task: Task | None = None,
    reader: StandardsReader | None = None,
) -> str:
    if task is not None:
        return _step_title_from_graph(task, step_id, planning, reader=reader)
    if planning:
        graph_titles = planning.get("graph_step_titles")
        if isinstance(graph_titles, dict) and step_id in graph_titles:
            return str(graph_titles[step_id])
    return step_id.replace("_", " ").title()


def mawp_step_title(
    step_id: str,
    planning: dict[str, Any] | None = None,
    *,
    task: Task | None = None,
    reader: StandardsReader | None = None,
) -> str:
    return pipe_wall_step_title(step_id, planning, task=task, reader=reader)


def _is_proposed_default(fact: Fact) -> bool:
    return (
        fact.fact_class == FactClass.DEFAULT_CONFIRMED
        and fact.validation.status == ValidationStatus.PENDING
    )


def _plan_field_resolved(task: Task, field: str) -> bool:
    from engine.planner.plan_selection import engineering_plan_for_task

    plan = engineering_plan_for_task(task)
    if plan is None:
        return False
    canonical = api_parameter_id(field)
    for req in plan.requirements.values():
        if req.field not in {field, canonical}:
            continue
        if req.status == "resolved":
            return True
    return False


def _timeline_input_step_resolved(
    task: Task,
    step_id: str,
    all_missing: set[str],
) -> bool:
    from engine.reference.parameter_keys import active_fact_for_key

    canonical_id = api_parameter_id(step_id)
    existing = active_fact_for_key(task, canonical_id)
    if existing is not None:
        if _is_proposed_default(existing):
            return False
        missing_canonical = {api_parameter_id(item) for item in all_missing}
        if fact_scalar_value(existing) is not None and canonical_id not in missing_canonical:
            return True
    return _plan_field_resolved(task, canonical_id)


def input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    if step_id == "allowable_stress":
        if task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None:
            return True
    if _timeline_input_step_resolved(task, step_id, all_missing):
        return True
    od = task.fact_store.active_fact("outside_diameter")
    if step_id == "outside_diameter" and od is not None:
        if (
            fact_scalar_value(od) is not None
            and not _is_proposed_default(od)
            and step_id not in all_missing
        ):
            return True
    thickness = task.fact_store.active_fact("actual_wall_thickness")
    if step_id == "actual_wall_thickness" and thickness is not None:
        if (
            fact_scalar_value(thickness) is not None
            and not _is_proposed_default(thickness)
            and step_id not in all_missing
        ):
            return True
    return False


def workflow_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    return input_step_done(task, step_id, all_missing)


def pipe_wall_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    return input_step_done(task, step_id, all_missing)


def mawp_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    return input_step_done(task, step_id, all_missing)


__all__ = [
    "HIDDEN_TIMELINE_INPUTS",
    "_HIDDEN_TIMELINE_INPUTS",
    "_hidden_timeline_inputs",
    "_pipe_wall_step_applies",
    "_pipe_wall_uses_inside_diameter",
    "_step_applies_for_timeline",
    "collect_all_missing",
    "collection_step_order",
    "composer_parameter_id",
    "composer_parameter_ids",
    "has_timeline_input_label",
    "hidden_timeline_inputs",
    "input_step_done",
    "mawp_input_step_done",
    "mawp_step_title",
    "parameter_collection_index",
    "pipe_wall_input_step_done",
    "pipe_wall_step_title",
    "revealed_input_ids",
    "revealed_mawp_input_ids",
    "revealed_pipe_wall_input_ids",
    "step_applies_for_timeline",
    "submittable_parameter_ids",
    "sync_timeline_input_order",
    "timeline_step_id_for_parameter",
    "workflow_input_step_done",
    "workflow_step_title",
]
