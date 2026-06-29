"""Dynamic workflow timeline and revealed parameter ordering."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.navigation_phases import allowed_fields_for_phase
from engine.graph.graph_timeline import graph_input_step_order, graph_step_titles
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from models.input import InputStatus
from models.planning import NavigationPhase
from models.task import Task

PIPE_WALL_NAVIGATION_PHASES: tuple[str, ...] = (
    "expansion_assumptions",
    "path_decisions",
    "parameter_gathering",
    "coefficient_resolution",
    "execution_assumptions",
    "definition_equation_completion",
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

_HIDDEN_TIMELINE_INPUTS = frozenset({"straight_pipe_section", "d_input_mode", "thin_wall"})
_MAWP_HIDDEN_TIMELINE_INPUTS = frozenset(
    {"straight_pipe_section", "geometry_input_mode", "thin_wall", "d_input_mode"}
)

MAWP_NAVIGATION_PHASES: tuple[str, ...] = (
    "expansion_assumptions",
    "path_decisions",
    "parameter_gathering",
    "coefficient_resolution",
    "ready",
)

MAWP_INPUT_STEP_ORDER: tuple[str, ...] = (
    "geometry_input_mode",
    "nominal_pipe_size",
    "pipe_schedule",
    "outside_diameter",
    "actual_wall_thickness",
    "corrosion_allowance",
    "material",
    "design_temperature",
    "joint_category",
    "allowable_stress",
    "weld_joint_efficiency",
    "weld_strength_reduction",
    "temperature_coefficient",
)

MAWP_STEP_TITLES: dict[str, str] = {
    "geometry_input_mode": "Geometry input mode",
    "nominal_pipe_size": "Nominal pipe size",
    "pipe_schedule": "Pipe schedule",
    "outside_diameter": "Outside diameter",
    "actual_wall_thickness": "Actual wall thickness",
    "corrosion_allowance": "Corrosion allowance",
    "material": "Material",
    "design_temperature": "Design temperature",
    "joint_category": "Joint category",
    "allowable_stress": "Allowable stress (S)",
    "weld_joint_efficiency": "Joint quality factor (E)",
    "weld_strength_reduction": "Weld strength reduction (W)",
    "temperature_coefficient": "Coefficient Y",
    "mawp": "Maximum Allowable Working Pressure (MAWP)",
    "report": "Report",
}


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
    loading = task.inputs.get("pressure_loading")
    loading_value = getattr(loading, "value", None) if loading is not None else None
    return loading_value in {"internal_pressure", "external_pressure"}


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

    graph_order = planning.get("graph_input_order")
    step_order = tuple(graph_order) if isinstance(graph_order, list) and graph_order else PIPE_WALL_INPUT_STEP_ORDER

    ordered: list[str] = []
    for step_id in step_order:
        if step_id in revealed:
            ordered.append(step_id)

    extras = sorted(revealed.difference(step_order))
    ordered.extend(extras)
    return ordered


def _mawp_geometry_mode(task: Task) -> str | None:
    mode = field_value("geometry_input_mode", task.inputs)
    if mode in {"nps_and_schedule", "direct_od_and_thickness"}:
        return str(mode)
    return None


def _mawp_step_applies(task: Task, step_id: str) -> bool:
    mode = _mawp_geometry_mode(task)
    if step_id == "nominal_pipe_size" or step_id == "pipe_schedule":
        return mode != "direct_od_and_thickness"
    if step_id in {"outside_diameter", "actual_wall_thickness"}:
        return mode != "nps_and_schedule"
    return True


def revealed_mawp_input_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    phase_missing = planning.get("phase_missing") or {}
    current_phase = str(planning.get("current_phase") or "")

    revealed: set[str] = set()
    for input_id in task.inputs:
        if input_id not in _MAWP_HIDDEN_TIMELINE_INPUTS:
            revealed.add(input_id)

    if current_phase and isinstance(phase_missing, dict):
        for phase in MAWP_NAVIGATION_PHASES:
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
                if str(item) not in _MAWP_HIDDEN_TIMELINE_INPUTS
            )

    if task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None:
        revealed.add("allowable_stress")

    ordered: list[str] = []
    for step_id in MAWP_INPUT_STEP_ORDER:
        if step_id in revealed and _mawp_step_applies(task, step_id):
            ordered.append(step_id)

    extras = sorted(revealed.difference(MAWP_INPUT_STEP_ORDER))
    for step_id in extras:
        if step_id not in _MAWP_HIDDEN_TIMELINE_INPUTS and _mawp_step_applies(task, step_id):
            ordered.append(step_id)
    return ordered


def _workflow_id(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")


def _hidden_timeline_inputs(task: Task) -> frozenset[str]:
    if is_mawp_task(task):
        return _MAWP_HIDDEN_TIMELINE_INPUTS
    return _HIDDEN_TIMELINE_INPUTS


def _input_step_order(task: Task) -> tuple[str, ...]:
    if is_mawp_task(task):
        return MAWP_INPUT_STEP_ORDER
    return PIPE_WALL_INPUT_STEP_ORDER


def _navigation_phases(task: Task) -> tuple[str, ...]:
    if is_mawp_task(task):
        return MAWP_NAVIGATION_PHASES
    return PIPE_WALL_NAVIGATION_PHASES


def revealed_input_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    if is_mawp_task(task):
        return revealed_mawp_input_ids(task, planning)
    return revealed_pipe_wall_input_ids(task, planning)


def _ordered_submittable_ids(task: Task, candidates: set[str]) -> list[str]:
    hidden = _hidden_timeline_inputs(task)
    step_order = _input_step_order(task)
    ordered: list[str] = []
    for step_id in step_order:
        if step_id in candidates and (not is_mawp_task(task) or _mawp_step_applies(task, step_id)):
            ordered.append(step_id)
    for item in sorted(candidates.difference(step_order)):
        if item not in hidden and (not is_mawp_task(task) or _mawp_step_applies(task, item)):
            ordered.append(item)
    return ordered


def _phase_allowed_input_ids(
    task: Task,
    current_phase: str,
    planning: dict[str, Any] | None = None,
) -> frozenset[str]:
    allowlists = (planning or {}).get("phase_allowed_fields")
    if isinstance(allowlists, dict) and current_phase in allowlists:
        return frozenset(str(item) for item in allowlists[current_phase] if str(item))
    try:
        workflow = "mawp_design" if is_mawp_task(task) else None
        return allowed_fields_for_phase(NavigationPhase(current_phase), workflow=workflow)
    except ValueError:
        return frozenset()


def _unconfirmed_proposed_defaults_for_phase(
    task: Task,
    *,
    allowed_ids: frozenset[str],
    phase_fields: set[str],
) -> list[str]:
    hidden = _hidden_timeline_inputs(task)
    extras: list[str] = []
    for input_id, existing in task.inputs.items():
        if (
            input_id in allowed_ids
            and input_id not in phase_fields
            and input_id not in hidden
            and existing.status == InputStatus.PROPOSED_DEFAULT
        ):
            extras.append(input_id)
    return extras


def submittable_parameter_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    """Parameters the user may submit on the current navigation phase."""
    edit_session = task.outputs.get("edit_session")
    if isinstance(edit_session, dict) and edit_session.get("parameter"):
        return [str(edit_session["parameter"])]

    hidden = _hidden_timeline_inputs(task)
    phase_missing = planning.get("phase_missing") or {}
    current_phase = str(planning.get("current_phase") or "")
    if isinstance(phase_missing, dict) and current_phase:
        phase_fields = [
            str(item)
            for item in (phase_missing.get(current_phase) or [])
            if str(item) not in hidden and (not is_mawp_task(task) or _mawp_step_applies(task, str(item)))
        ]
        if phase_fields:
            allowed_ids = _phase_allowed_input_ids(task, current_phase, planning)
            extras = _unconfirmed_proposed_defaults_for_phase(
                task,
                allowed_ids=allowed_ids,
                phase_fields=set(phase_fields),
            )
            return _ordered_submittable_ids(task, set(phase_fields) | set(extras))

    requested_ids: list[str] = []
    for key in ("missing_assumptions", "missing_execution_assumptions", "missing_inputs"):
        for item in planning.get(key) or []:
            item_id = str(item)
            if item_id in hidden:
                continue
            if is_mawp_task(task) and not _mawp_step_applies(task, item_id):
                continue
            if item_id not in requested_ids:
                requested_ids.append(item_id)

    for input_id, existing in task.inputs.items():
        if (
            input_id not in hidden
            and existing.status == InputStatus.PROPOSED_DEFAULT
            and input_id not in requested_ids
            and (not is_mawp_task(task) or _mawp_step_applies(task, input_id))
        ):
            requested_ids.append(input_id)

    return requested_ids


def workflow_step_title(task: Task, step_id: str) -> str:
    if is_mawp_task(task):
        return MAWP_STEP_TITLES.get(step_id, step_id.replace("_", " ").title())
    return PIPE_WALL_STEP_TITLES.get(step_id, step_id.replace("_", " ").title())


def pipe_wall_step_title(step_id: str, planning: dict[str, Any] | None = None) -> str:
    if planning:
        graph_titles = planning.get("graph_step_titles")
        if isinstance(graph_titles, dict) and step_id in graph_titles:
            return str(graph_titles[step_id])
    return PIPE_WALL_STEP_TITLES.get(step_id, step_id.replace("_", " ").title())


def mawp_step_title(step_id: str) -> str:
    return MAWP_STEP_TITLES.get(step_id, step_id.replace("_", " ").title())


def workflow_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    if is_mawp_task(task):
        return mawp_input_step_done(task, step_id, all_missing)
    return pipe_wall_input_step_done(task, step_id, all_missing)


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


def mawp_input_step_done(task: Task, step_id: str, all_missing: set[str]) -> bool:
    existing = task.inputs.get(step_id)
    if existing is not None:
        if existing.status == InputStatus.PROPOSED_DEFAULT:
            return False
        if existing.value is not None and step_id not in all_missing:
            return True

    if step_id == "allowable_stress":
        return task.outputs.get("allowable_stress") is not None or task.outputs.get("S") is not None

    if step_id == "outside_diameter" and task.inputs.get("outside_diameter") is not None:
        od = task.inputs["outside_diameter"]
        if od.value is not None and od.status != InputStatus.PROPOSED_DEFAULT and step_id not in all_missing:
            return True

    if step_id == "actual_wall_thickness" and task.inputs.get("actual_wall_thickness") is not None:
        thickness = task.inputs["actual_wall_thickness"]
        if (
            thickness.value is not None
            and thickness.status != InputStatus.PROPOSED_DEFAULT
            and step_id not in all_missing
        ):
            return True

    return False
