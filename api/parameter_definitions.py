"""Build UI parameter definitions and handle structured input submission."""

from __future__ import annotations

from typing import Any

from ai.interaction_specs import default_pipe_wall_thickness_decision_interactions
from engine.executor.unit_manager import normalize_unit
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task

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
        "units": [],
        "default_unit": "dimensionless",
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

    requested_ids: list[str] = []
    for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
        for item in planning.get(key) or []:
            if item not in requested_ids:
                requested_ids.append(str(item))

    for input_id, existing in task.inputs.items():
        if existing.status == InputStatus.PROPOSED_DEFAULT and input_id not in requested_ids:
            requested_ids.append(input_id)

    if not requested_ids and _task_workflow_id(task) == PIPE_WALL_THICKNESS_DESIGN:
        requested_ids = list(planning.get("missing_inputs") or ["material", "design_pressure", "design_temperature"])

    parameters: list[dict[str, Any]] = []
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
            }
        )

    return parameters


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
) -> Task:
    task = manager.get_task(task_id)
    definitions = {item["name"]: item for item in build_parameter_definitions(task)}
    if parameter not in definitions:
        raise ValueError(f"Parameter is not currently requested: {parameter}")

    definition = definitions[parameter]
    coerced = _coerce_value(definition, value)
    _validate_against_spec(definition, coerced)

    resolved_unit = unit or definition.get("default_unit") or "dimensionless"
    if definition["type"] == "number" and definition.get("units"):
        resolved_unit = normalize_unit(resolved_unit)
    elif definition["type"] in {"dropdown", "checkbox", "material", "text", "multi_select"}:
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

    planning = task.outputs.get("planning_summary")
    if isinstance(planning, dict):
        for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions"):
            items = planning.get(key)
            if isinstance(items, list) and parameter in items:
                planning[key] = [item for item in items if item != parameter]

    return manager.get_task(task_id)
