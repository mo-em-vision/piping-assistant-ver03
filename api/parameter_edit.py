"""Assess and begin timeline parameter edits for desktop workflows."""

from __future__ import annotations

from typing import Any

from api.workflow_timeline import (
    PIPE_WALL_INPUT_STEP_ORDER,
    _HIDDEN_TIMELINE_INPUTS,
)
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.task import Task, TaskStatus

_PATH_SENSITIVE_INPUTS = frozenset({"pressure_loading"})
_DESIGN_SENSITIVE_INPUTS = frozenset(
    {
        "pressure_loading",
        "material",
        "design_temperature",
        "joint_category",
        "nominal_pipe_size",
        "outside_diameter",
    }
)

_EXECUTION_OUTPUT_KEYS = (
    "_execution_trace",
    "_validation_trace",
    "required_thickness",
    "t",
    "allowable_stress",
    "S",
    "minimum_required_thickness",
    "t_m",
    "thin_wall",
    "graph_version",
)


def downstream_input_ids(parameter_id: str) -> list[str]:
    if parameter_id not in PIPE_WALL_INPUT_STEP_ORDER:
        return []
    index = PIPE_WALL_INPUT_STEP_ORDER.index(parameter_id)
    return list(PIPE_WALL_INPUT_STEP_ORDER[index + 1 :])


def is_timeline_parameter_editable(task: Task, parameter_id: str) -> bool:
    if str(task.outputs.get("workflow") or "") != PIPE_WALL_THICKNESS_DESIGN:
        return False
    if parameter_id in _HIDDEN_TIMELINE_INPUTS or parameter_id not in PIPE_WALL_INPUT_STEP_ORDER:
        return False
    if parameter_id == "allowable_stress":
        return (
            parameter_id in task.inputs
            or task.outputs.get("allowable_stress") is not None
            or task.outputs.get("S") is not None
        )
    return parameter_id in task.inputs


def assess_parameter_edit(task: Task, parameter_id: str) -> dict[str, Any]:
    if not is_timeline_parameter_editable(task, parameter_id):
        raise ValueError(f"Parameter is not editable: {parameter_id}")

    downstream = downstream_input_ids(parameter_id)
    downstream_present = [item for item in downstream if item in task.inputs]
    has_execution = bool(
        task.outputs.get("_execution_trace")
        or task.outputs.get("required_thickness")
        or task.outputs.get("t")
    )

    affects_path = parameter_id in _PATH_SENSITIVE_INPUTS
    affects_design = (
        parameter_id in _DESIGN_SENSITIVE_INPUTS
        or bool(downstream_present)
        or has_execution
        or task.status in {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}
    )

    messages: list[str] = []
    if affects_path:
        messages.append(
            "Changing pressure loading may switch the governing calculation node "
            "(for example §304.1.2 vs §304.1.3)."
        )
    if has_execution or task.status == TaskStatus.COMPLETED:
        messages.append("Confirmed calculation results will be cleared and recomputed.")
    if downstream_present:
        messages.append(
            "Inputs collected after this parameter will be cleared: "
            + ", ".join(downstream_present)
            + "."
        )

    return {
        "parameter": parameter_id,
        "affects_path": affects_path,
        "affects_design": affects_design,
        "downstream_parameters": downstream_present,
        "message": " ".join(messages) if messages else None,
    }


def begin_parameter_edit(task: Task, parameter_id: str) -> dict[str, Any]:
    assessment = assess_parameter_edit(task, parameter_id)

    for downstream_id in downstream_input_ids(parameter_id):
        task.inputs.pop(downstream_id, None)

    for output_key in _EXECUTION_OUTPUT_KEYS:
        task.outputs.pop(output_key, None)

    if task.status in {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}:
        task.status = TaskStatus.AWAITING_INPUT

    task.outputs["edit_session"] = {
        "parameter": parameter_id,
        "affects_design": assessment["affects_design"],
        "affects_path": assessment["affects_path"],
        "message": assessment.get("message"),
    }

    return assessment


def active_edit_parameter(task: Task) -> str | None:
    edit_session = task.outputs.get("edit_session")
    if not isinstance(edit_session, dict):
        return None
    parameter = edit_session.get("parameter")
    return str(parameter) if parameter else None


def clear_edit_session(task: Task) -> None:
    task.outputs.pop("edit_session", None)
