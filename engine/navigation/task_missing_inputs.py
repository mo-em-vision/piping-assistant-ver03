"""Resolve missing input ids for a task from planning projection or graph."""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.graph.graph_engine import GraphEngine, normalize_root_id
from engine.planner.tools import GraphTools
from engine.navigation.missing_inputs import collect_all_missing
from engine.router import normalize_planning_workflow_id
from engine.state.goal_projection import planning_projection
from models.task import Task

if TYPE_CHECKING:
    from engine.reference.standards_reader import StandardsReader


def resolve_task_workflow_id(task: Task) -> str:
    explicit = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()
    if explicit:
        return normalize_planning_workflow_id(explicit)
    normalized_id = task.task_id.replace("-", "_").lower()
    if "pipe_wall_thickness_design" in normalized_id or normalized_id.startswith("pipe_wall"):
        return "pipe_wall_thickness_design"
    if "mawp" in normalized_id:
        return "mawp_design"
    return ""


def missing_inputs_for_task(
    task: Task,
    *,
    reader: StandardsReader | None = None,
) -> list[str]:
    """Return missing input ids from planning projection or graph evaluation."""
    planning = planning_projection(task)
    if planning:
        missing = sorted(collect_all_missing(planning))
        if missing:
            return missing

    workflow_id = resolve_task_workflow_id(task)
    if not workflow_id or reader is None:
        return []

    graph = GraphEngine()
    slug = normalize_root_id(workflow_id)
    inputs = dict(task.fact_store.active_facts())
    preview = graph.build_plan(
        task_id=task.task_id,
        root_id=slug,
        inputs=inputs,
        reader=reader,
    )
    missing = graph.required_user_inputs(
        slug,
        reader,
        existing_inputs=set(inputs.keys()),
        task_inputs=inputs,
        plan=preview,
    )
    if missing:
        return list(missing)

    graph_tools = GraphTools(reader)
    assumption_eval = graph_tools.evaluate_assumptions(slug, existing_inputs=inputs, plan=preview)
    expansion_eval = graph_tools.evaluate_expansion_interactions(
        slug,
        existing_inputs=inputs,
        plan=preview,
    )
    execution_eval = graph_tools.evaluate_execution_assumptions(
        slug,
        existing_inputs=inputs,
        plan=preview,
    )
    return list(
        dict.fromkeys(
            list(assumption_eval.missing_fields)
            + list(expansion_eval.missing_fields)
            + list(execution_eval.missing_fields)
        )
    )
