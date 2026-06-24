"""Dynamic pipe-wall workflow timeline and revealed parameter ordering."""

from __future__ import annotations

from typing import Any

from models.input import InputStatus
from models.task import Task

PIPE_WALL_NAVIGATION_PHASES: tuple[str, ...] = (
    "expansion_assumptions",
    "path_decisions",
    "parameter_gathering",
    "coefficient_resolution",
    "execution_assumptions",
    "ready",
)

PIPE_WALL_INPUT_STEP_ORDER: tuple[str, ...] = (
    "pressure_loading",
    "material",
    "design_pressure",
    "design_temperature",
    "nominal_pipe_size",
    "outside_diameter",
    "external_design_pressure",
    "joint_category",
    "allowable_stress",
    "weld_joint_efficiency",
    "weld_strength_reduction",
    "temperature_coefficient",
    "corrosion_allowance",
)

PIPE_WALL_STEP_TITLES: dict[str, str] = {
    "pressure_loading": "Pressure loading",
    "material": "Material",
    "design_pressure": "Design pressure",
    "design_temperature": "Design temperature",
    "nominal_pipe_size": "Nominal pipe size",
    "outside_diameter": "Outside diameter",
    "external_design_pressure": "External design pressure",
    "joint_category": "Joint category",
    "allowable_stress": "Allowable stress (S)",
    "weld_joint_efficiency": "Joint efficiency (E)",
    "weld_strength_reduction": "Weld strength reduction (W)",
    "temperature_coefficient": "Temperature coefficient (Y)",
    "corrosion_allowance": "Corrosion allowance",
    "thickness": "Thickness",
    "report": "Report",
}

_HIDDEN_TIMELINE_INPUTS = frozenset({"straight_pipe_section", "d_input_mode"})


def collect_all_missing(planning: dict[str, Any]) -> set[str]:
    all_missing: set[str] = set()
    for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
        all_missing.update(str(item) for item in (planning.get(key) or []))
    phase_missing = planning.get("phase_missing") or {}
    if isinstance(phase_missing, dict):
        for fields in phase_missing.values():
            if isinstance(fields, list):
                all_missing.update(str(item) for item in fields)
    return all_missing


def revealed_pipe_wall_input_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    """Input ids that should appear in timeline and parameter state for the active path."""
    phase_missing = planning.get("phase_missing") or {}
    current_phase = str(planning.get("current_phase") or "")

    revealed: set[str] = set()
    for input_id in task.inputs:
        if input_id not in _HIDDEN_TIMELINE_INPUTS:
            revealed.add(input_id)

    if current_phase and isinstance(phase_missing, dict):
        for phase in PIPE_WALL_NAVIGATION_PHASES:
            if phase == "ready":
                break
            fields = phase_missing.get(phase) or []
            if isinstance(fields, list):
                revealed.update(str(item) for item in fields)
            if phase == current_phase:
                break
    else:
        for key in ("missing_inputs", "missing_assumptions"):
            revealed.update(
                str(item)
                for item in (planning.get(key) or [])
                if str(item) not in _HIDDEN_TIMELINE_INPUTS
            )

    if task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None:
        revealed.add("allowable_stress")

    ordered: list[str] = []
    for step_id in PIPE_WALL_INPUT_STEP_ORDER:
        if step_id in revealed:
            ordered.append(step_id)

    extras = sorted(revealed.difference(PIPE_WALL_INPUT_STEP_ORDER))
    ordered.extend(extras)
    return ordered


def submittable_parameter_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    """Parameters the user may submit on the current navigation phase."""
    edit_session = task.outputs.get("edit_session")
    if isinstance(edit_session, dict) and edit_session.get("parameter"):
        return [str(edit_session["parameter"])]

    phase_missing = planning.get("phase_missing") or {}
    current_phase = str(planning.get("current_phase") or "")
    if isinstance(phase_missing, dict) and current_phase:
        phase_fields = phase_missing.get(current_phase) or []
        if phase_fields:
            return [str(item) for item in phase_fields if str(item) not in _HIDDEN_TIMELINE_INPUTS]

    requested_ids: list[str] = []
    for key in ("missing_assumptions", "missing_execution_assumptions", "missing_inputs"):
        for item in planning.get(key) or []:
            item_id = str(item)
            if item_id in _HIDDEN_TIMELINE_INPUTS:
                continue
            if item_id not in requested_ids:
                requested_ids.append(item_id)

    for input_id, existing in task.inputs.items():
        if (
            input_id not in _HIDDEN_TIMELINE_INPUTS
            and existing.status == InputStatus.PROPOSED_DEFAULT
            and input_id not in requested_ids
        ):
            requested_ids.append(input_id)

    return requested_ids


def pipe_wall_step_title(step_id: str) -> str:
    return PIPE_WALL_STEP_TITLES.get(step_id, step_id.replace("_", " ").title())


def pipe_wall_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    existing = task.inputs.get(step_id)
    if existing is not None:
        if existing.status == InputStatus.PROPOSED_DEFAULT:
            return False
        if existing.value is not None and step_id not in all_missing:
            return True

    if step_id == "allowable_stress":
        return task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None

    return False
