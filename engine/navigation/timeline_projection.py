"""Graph-driven timeline step visibility — no workflow-specific branching."""

from __future__ import annotations

from engine.graph.assumption_checker import field_value
from engine.state.task_facts import active_facts
from models.task import Task

HIDDEN_TIMELINE_INPUTS = frozenset(
    {"d_input_mode", "thin_wall", "outside_diameter__resolution_branch"}
)

_INSIDE_DIAMETER_STEP = "inside_diameter"
_NPS_OD_STEPS = frozenset({"nominal_pipe_size", "outside_diameter"})


def hidden_timeline_inputs(task: Task) -> frozenset[str]:
    """Internal fact keys that must not appear as timeline rows."""
    del task
    return HIDDEN_TIMELINE_INPUTS


def uses_inside_diameter_path(task: Task) -> bool:
    """True when the active graph path collects inside diameter instead of NPS/OD."""
    return field_value(_INSIDE_DIAMETER_STEP, active_facts(task)) is not None


def step_applies_for_timeline(task: Task, step_id: str) -> bool:
    """Hide diameter inputs that are mutually exclusive on the active resolution branch."""
    if uses_inside_diameter_path(task):
        return step_id not in _NPS_OD_STEPS
    if step_id == _INSIDE_DIAMETER_STEP:
        return False
    return True


def ensure_diameter_timeline_pair(task: Task, revealed: set[str]) -> None:
    """When NPS/OD path is active, show both diameter entry rows together."""
    if uses_inside_diameter_path(task):
        return
    if "nominal_pipe_size" in revealed or "outside_diameter" in revealed:
        revealed.add("nominal_pipe_size")
        revealed.add("outside_diameter")
