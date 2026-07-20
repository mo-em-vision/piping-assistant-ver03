"""Map graph parameter ids to composer and timeline row ids."""

from __future__ import annotations

from engine.navigation.timeline_row_ids import timeline_row_id
from engine.reference.parameter_keys import api_parameter_id
from models.task import Task


def composer_parameter_id(task: Task, parameter_id: str) -> str:
    """Map graph parameter ids to the parameter id shown in the workflow composer."""
    return parameter_id


def composer_parameter_ids(task: Task, parameter_ids: list[str]) -> list[str]:
    mapped: list[str] = []
    for parameter_id in parameter_ids:
        resolved = composer_parameter_id(task, parameter_id)
        if resolved not in mapped:
            mapped.append(resolved)
    return mapped


def timeline_step_id_for_parameter(
    task: Task,
    parameter_id: str,
    *,
    revealed: list[str] | None = None,
) -> str:
    """Map composer/current_ask parameter ids to timeline row ids."""
    parameter_id = timeline_row_id(api_parameter_id(parameter_id))
    candidates = [parameter_id]
    if parameter_id in {"nominal_pipe_size", "outside_diameter"}:
        candidates.extend(["nominal_pipe_size", "outside_diameter"])
    if revealed:
        revealed_set = {timeline_row_id(api_parameter_id(item)) for item in revealed}
        for candidate in candidates:
            if timeline_row_id(api_parameter_id(candidate)) in revealed_set:
                return timeline_row_id(api_parameter_id(candidate))
    return parameter_id
