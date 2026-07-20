"""Workflow goal completion steps for timeline presentation."""

from __future__ import annotations

from dataclasses import dataclass

from engine.planner.workflow_goal_metadata import resolve_root_goal_spec
from engine.reference.standards_reader import StandardsReader

_TIMELINE_STEP_ALIASES: dict[str, str] = {
    "minimum_required_thickness": "thickness",
    "maximum_allowable_working_pressure": "mawp",
}

_GOAL_OUTPUT_KEYS: dict[str, tuple[str, ...]] = {
    "minimum_required_thickness": ("required_thickness", "thickness", "t"),
    "maximum_allowable_working_pressure": ("mawp", "MAWP"),
}


@dataclass(frozen=True)
class TimelineCompletionStep:
    step_id: str
    title: str
    output_keys: tuple[str, ...]


def timeline_completion_steps(
    reader: StandardsReader,
    workflow_id: str,
) -> tuple[TimelineCompletionStep, ...]:
    """Derive calculation + report timeline tail steps from workflow goal metadata."""
    spec = resolve_root_goal_spec(reader, workflow_id)
    calc_step_id = _TIMELINE_STEP_ALIASES.get(spec.target_field, spec.target_field)
    output_keys = _GOAL_OUTPUT_KEYS.get(spec.target_field, (spec.target_field,))
    calc_title = spec.title or calc_step_id.replace("_", " ").title()
    return (
        TimelineCompletionStep(
            step_id=calc_step_id,
            title=calc_title,
            output_keys=output_keys,
        ),
        TimelineCompletionStep(
            step_id="report",
            title="Report",
            output_keys=(),
        ),
    )


def goal_output_value(task_outputs: dict, output_keys: tuple[str, ...]):
    for key in output_keys:
        if task_outputs.get(key) is not None:
            return task_outputs.get(key)
    return None
