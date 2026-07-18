"""Workflow identity and pipe-wall path step filters."""

from __future__ import annotations

from engine.graph.assumption_checker import field_value
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.state.task_facts import active_facts
from models.fact import fact_scalar_value
from models.task import Task

HIDDEN_TIMELINE_INPUTS = frozenset(
    {"d_input_mode", "thin_wall", "outside_diameter__resolution_branch"}
)


def is_mawp_task(task: Task) -> bool:
    workflow = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if workflow in {MAWP_DESIGN, "B313-MAWP-DESIGN", "mawp_design"}:
        return True
    return "mawp" in workflow.lower()


def is_pipe_wall_thickness_task(task: Task) -> bool:
    if is_mawp_task(task):
        return False
    workflow = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if workflow in {PIPE_WALL_THICKNESS_DESIGN, "B313-PIPE-WALL-THICKNESS-DESIGN"}:
        return True
    if "pipe_wall_thickness" in workflow.lower():
        return True
    loading = task.fact_store.active_fact("pressure_design_case")
    loading_value = fact_scalar_value(loading) if loading is not None else None
    return loading_value in {"internal_pressure", "external_pressure"}


def pipe_wall_uses_inside_diameter(task: Task) -> bool:
    return field_value("inside_diameter", active_facts(task)) is not None


def pipe_wall_step_applies(task: Task, step_id: str) -> bool:
    if is_mawp_task(task):
        return True
    if pipe_wall_uses_inside_diameter(task):
        return step_id not in {"nominal_pipe_size", "outside_diameter"}
    return step_id != "inside_diameter"


def hidden_timeline_inputs(task: Task) -> frozenset[str]:
    return HIDDEN_TIMELINE_INPUTS


def step_applies_for_timeline(task: Task, step_id: str) -> bool:
    if is_pipe_wall_thickness_task(task):
        return pipe_wall_step_applies(task, step_id)
    return True
