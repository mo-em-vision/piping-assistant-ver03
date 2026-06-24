"""Build UI parameter definitions and handle structured input submission."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai.interaction_specs import default_pipe_wall_thickness_decision_interactions
from engine.executor.allowable_stress_resolver import apply_allowable_stress_lookup
from engine.executor.coefficient_lookup import apply_coefficient_lookups
from engine.executor.nps_input_resolver import apply_nominal_pipe_size_lookup
from engine.executor.unit_manager import normalize_unit
from engine.reference.material_resolver import canonical_material_id
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task

from api.parameter_edit import active_edit_parameter, clear_edit_session
from api.workflow_timeline import revealed_pipe_wall_input_ids, submittable_parameter_ids

_PARAMETER_SPECS: dict[str, dict[str, Any]] = {
    "material": {
        "label": "Material",
        "type": "material",
        "units": [],
        "default_unit": "dimensionless",
    },
    "design_pressure": {
        "label": "Design Pressure",
        "type": "number",
        "units": ["bar", "psi", "MPa", "kPa"],
        "default_unit": "bar",
        "validation": {"min": 0},
    },
    "design_temperature": {
        "label": "Design Temperature",
        "type": "number",
        "units": ["C", "F"],
        "default_unit": "C",
        "validation": {"min": -273},
    },
    "outside_diameter": {
        "label": "Outside Diameter",
        "type": "number",
        "units": ["in", "mm"],
        "default_unit": "in",
        "validation": {"min": 0},
    },
    "nominal_pipe_size": {
        "label": "Nominal Pipe Size",
        "type": "text",
        "units": ["NPS", "DN"],
        "default_unit": "NPS",
    },
    "allowable_stress": {
        "label": "Allowable Stress",
        "type": "number",
        "units": ["MPa", "psi", "bar"],
        "default_unit": "MPa",
        "validation": {"min": 0},
    },
    "corrosion_allowance": {
        "label": "Corrosion Allowance",
        "type": "number",
        "units": ["in", "mm"],
        "default_unit": "mm",
        "validation": {"min": 0},
    },
    "straight_pipe_section": {
        "label": "Straight Pipe Section",
        "type": "checkbox",
        "units": [],
        "default_unit": "dimensionless",
        "default_value": True,
    },
    "pressure_loading": {
        "label": "Pressure Loading",
        "type": "dropdown",
        "units": [],
        "default_unit": "dimensionless",
        "options": [
            {"value": "internal_pressure", "label": "Internal pressure"},
            {"value": "external_pressure", "label": "External pressure"},
        ],
    },
    "d_input_mode": {
        "label": "Diameter Input Mode",
        "type": "dropdown",
        "units": [],
        "default_unit": "dimensionless",
        "options": [
            {"value": "nps_lookup", "label": "NPS lookup"},
            {"value": "direct_od", "label": "Direct outside diameter"},
        ],
    },
    "joint_category": {
        "label": "Joint Category",
        "type": "dropdown",
        "units": [],
        "default_unit": "dimensionless",
        "options": [
            {"value": "seamless", "label": "Seamless"},
            {"value": "welded", "label": "Welded"},
        ],
    },
    "weld_joint_efficiency": {
        "label": "Weld Joint Efficiency",
        "type": "number",
        "units": [],
        "default_unit": "dimensionless",
        "validation": {"min": 0, "max": 1},
    },
    "weld_strength_reduction": {
        "label": "Weld Strength Reduction",
        "type": "number",
        "units": [],
        "default_unit": "dimensionless",
        "validation": {"min": 0, "max": 1},
    },
    "temperature_coefficient": {
        "label": "Temperature Coefficient",
        "type": "number",
        "units": [],
        "default_unit": "dimensionless",
        "validation": {"min": 0, "max": 1},
    },
}


def _interaction_options() -> dict[str, list[dict[str, str]]]:
    options: dict[str, list[dict[str, str]]] = {}
    for spec in default_pipe_wall_thickness_decision_interactions():
        if spec.options:
            options[spec.variable] = [
                {"value": option, "label": option.replace("_", " ").title()}
                for option in spec.options
            ]
    return options


_INTERACTION_OPTIONS = _interaction_options()


def _base_spec(parameter_id: str) -> dict[str, Any]:
    if parameter_id in _PARAMETER_SPECS:
        return dict(_PARAMETER_SPECS[parameter_id])
    return {
        "label": parameter_id.replace("_", " ").title(),
        "type": "text",
        "units": [],
        "default_unit": "dimensionless",
    }


def _parameter_status(task: Task, parameter_id: str) -> str:
    if active_edit_parameter(task) == parameter_id:
        return "pending"

    existing = task.inputs.get(parameter_id)
    if existing is None:
        return "pending"
    if existing.status == InputStatus.PROPOSED_DEFAULT:
        return "confirmation_required"
    if existing.status in {InputStatus.CONFIRMED, InputStatus.USER_OVERRIDE}:
        return "confirmed"
    if existing.value is not None:
        return "pending"
    return "pending"


def _current_value(task: Task, parameter_id: str) -> Any:
    existing = task.inputs.get(parameter_id)
    if existing is None:
        return None
    return existing.value


def build_parameter_definitions(task: Task) -> list[dict[str, Any]]:
    planning = task.outputs.get("planning_summary") or {}
    if not isinstance(planning, dict):
        planning = {}

    requested_ids = _requested_parameter_ids(task, planning)
    submittable_ids = set(submittable_parameter_ids(task, planning))

    parameters: list[dict[str, Any]] = []
    editing = active_edit_parameter(task)
    for parameter_id in requested_ids:
        spec = _base_spec(parameter_id)
        options = spec.get("options") or _INTERACTION_OPTIONS.get(parameter_id)
        existing = task.inputs.get(parameter_id)
        parameters.append(
            {
                "name": parameter_id,
                "label": spec["label"],
                "type": spec["type"],
                "required": True,
                "units": list(spec.get("units") or []),
                "default_unit": spec.get("default_unit", "dimensionless"),
                "default_value": existing.default if existing and existing.default is not None else spec.get("default_value"),
                "value": _current_value(task, parameter_id),
                "options": options,
                "validation": spec.get("validation"),
                "status": _parameter_status(task, parameter_id),
                "requires_confirmation": bool(existing.requires_confirmation) if existing else False,
                "guidance": _parameter_guidance(planning, parameter_id),
                "editing": editing == parameter_id,
                "submittable": parameter_id in submittable_ids,
            }
        )

    return parameters


def _requested_parameter_ids(task: Task, planning: dict[str, Any]) -> list[str]:
    if _task_workflow_id(task) == PIPE_WALL_THICKNESS_DESIGN:
        requested = revealed_pipe_wall_input_ids(task, planning)
        editing = active_edit_parameter(task)
        if editing and editing not in requested:
            requested = [editing, *requested]
        return requested

    requested_ids: list[str] = []
    for key in ("missing_assumptions", "missing_execution_assumptions", "missing_inputs"):
        for item in planning.get(key) or []:
            item_id = str(item)
            if item_id == "straight_pipe_section":
                continue
            if item_id not in requested_ids:
                requested_ids.append(item_id)

    for input_id, existing in task.inputs.items():
        if (
            input_id != "straight_pipe_section"
            and existing.status == InputStatus.PROPOSED_DEFAULT
            and input_id not in requested_ids
        ):
            requested_ids.append(input_id)

    return requested_ids


def _parameter_guidance(planning: dict[str, Any], parameter_id: str) -> str | None:
    phase_missing = planning.get("phase_missing") or {}
    phase_questions = planning.get("phase_questions") or {}
    if not isinstance(phase_missing, dict) or not isinstance(phase_questions, dict):
        return None
    for phase, fields in phase_missing.items():
        if not isinstance(fields, list) or parameter_id not in fields:
            continue
        questions = phase_questions.get(phase)
        if not isinstance(questions, list):
            continue
        index = fields.index(parameter_id)
        if index < len(questions):
            return str(questions[index])
    return None


def _task_workflow_id(task: Task) -> str:
    workflow = task.outputs.get("workflow")
    return str(workflow) if workflow else ""


def _coerce_value(parameter: dict[str, Any], raw_value: Any) -> Any:
    param_type = parameter["type"]
    if param_type == "checkbox":
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, str):
            return raw_value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(raw_value)
    if param_type == "number":
        if raw_value is None or raw_value == "":
            raise ValueError("A numeric value is required.")
        return float(raw_value)
    if param_type == "multi_select":
        if not isinstance(raw_value, list):
            raise ValueError("Expected a list of selected values.")
        return [str(item) for item in raw_value]
    return raw_value


def _validate_against_spec(parameter: dict[str, Any], value: Any) -> None:
    validation = parameter.get("validation") or {}
    if parameter["type"] == "number" and isinstance(value, (int, float)):
        minimum = validation.get("min")
        maximum = validation.get("max")
        if minimum is not None and value < minimum:
            raise ValueError(f"Value must be at least {minimum}.")
        if maximum is not None and value > maximum:
            raise ValueError(f"Value must be at most {maximum}.")
    options = parameter.get("options") or []
    if options and parameter["type"] in {"dropdown", "multi_select"}:
        allowed = {item["value"] if isinstance(item, dict) else item for item in options}
        if parameter["type"] == "dropdown" and str(value) not in allowed:
            raise ValueError("Selected value is not allowed.")
        if parameter["type"] == "multi_select":
            invalid = [item for item in value if item not in allowed]
            if invalid:
                raise ValueError("One or more selected values are not allowed.")


def submit_task_input(
    manager: TaskStateManager,
    task_id: str,
    *,
    parameter: str,
    value: Any,
    unit: str | None,
    standards_root: Path | None = None,
) -> Task:
    task = manager.get_task(task_id)
    planning = task.outputs.get("planning_summary")
    if not isinstance(planning, dict):
        planning = {}

    allowed_ids = set(submittable_parameter_ids(task, planning))
    if parameter not in allowed_ids:
        raise ValueError(f"Parameter is not currently requested: {parameter}")

    definitions = {item["name"]: item for item in build_parameter_definitions(task)}
    if parameter not in definitions:
        raise ValueError(f"Parameter is not currently requested: {parameter}")

    definition = definitions[parameter]
    coerced = _coerce_value(definition, value)
    _validate_against_spec(definition, coerced)

    if parameter == "material" and standards_root is not None:
        resolved_material = canonical_material_id(str(coerced), standards_root=standards_root)
        if resolved_material is not None:
            coerced = resolved_material

    resolved_unit = unit or definition.get("default_unit") or "dimensionless"
    if definition["type"] == "number" and definition.get("units"):
        resolved_unit = normalize_unit(resolved_unit)
    elif definition["type"] == "text" and definition.get("units"):
        resolved_unit = str(resolved_unit).strip().upper()
    elif definition["type"] in {"dropdown", "checkbox", "material", "multi_select"}:
        resolved_unit = definition.get("default_unit", "dimensionless")

    engineering_input = EngineeringInput(
        input_id=parameter,
        value=coerced,
        unit=resolved_unit,
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
        default=definition.get("default_value"),
        requires_confirmation=False,
    )
    manager.store_input(task_id, engineering_input)

    task = manager.get_task(task_id)
    if parameter == "nominal_pipe_size":
        if standards_root is None:
            raise ValueError("Standards root is required to resolve nominal pipe size.")
        apply_nominal_pipe_size_lookup(task, standards_root)
        manager.replace_task(task_id, task)
        task = manager.get_task(task_id)

    if parameter in ("material", "design_temperature"):
        if standards_root is None:
            raise ValueError("Standards root is required to resolve allowable stress.")
        apply_allowable_stress_lookup(task, standards_root)
        manager.replace_task(task_id, task)
        task = manager.get_task(task_id)

    if parameter in ("material", "design_temperature", "joint_category"):
        if standards_root is None:
            raise ValueError("Standards root is required to resolve weld joint coefficients.")
        apply_coefficient_lookups(task, standards_root)
        manager.replace_task(task_id, task)
        task = manager.get_task(task_id)

    if active_edit_parameter(task) == parameter:
        clear_edit_session(task)

    planning = task.outputs.get("planning_summary")
    if isinstance(planning, dict):
        for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
            items = planning.get(key)
            if isinstance(items, list) and parameter in items:
                planning[key] = [item for item in items if item != parameter]
        phase_missing = planning.get("phase_missing")
        if isinstance(phase_missing, dict):
            for phase, fields in phase_missing.items():
                if isinstance(fields, list) and parameter in fields:
                    planning["phase_missing"][phase] = [item for item in fields if item != parameter]

    return manager.get_task(task_id)
