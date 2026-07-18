"""Build structured question specs from PARAM node metadata — no user-facing prose."""

from __future__ import annotations

from engine.reference.parameter_keys import load_parameter_node_metadata, param_node_id_for_input
from engine.units.unit_ids import symbol_from_unit_id
from engine.units.unit_registry import get_unit_registry
from models.engineering_plan import QuestionSpec

_DESIGNATION_DIMENSIONS = frozenset({"DIM-material-designation", "DIM-designation"})

_REASON_CODES: dict[str, str] = {
    "internal_design_gage_pressure": "required_by_asme_b31_3_304_1_2_internal_pressure",
    "outside_diameter": "required_for_pressure_design_thickness",
    "nominal_pipe_size": "required_for_outside_diameter_lookup",
    "diameter_input_mode": "required_for_pressure_design_thickness",
    "material_grade": "required_for_allowable_stress_lookup",
    "design_temperature": "required_for_allowable_stress_and_coefficients",
    "corrosion_allowance": "required_for_minimum_required_thickness",
    "pipe_construction_type": "required_for_weld_joint_efficiency_lookup",
    "straight_pipe_section": "required_for_workflow_expansion",
    "pressure_design_case": "required_for_path_selection",
    "external_design_pressure": "required_by_asme_b31_3_304_1_3_external_pressure",
}

_PRIORITY: dict[str, int] = {
    "straight_pipe_section": 0,
    "pressure_design_case": 0,
    "internal_design_gage_pressure": 1,
    "diameter_input_mode": 2,
    "outside_diameter": 2,
    "nominal_pipe_size": 2,
    "material_grade": 3,
    "design_temperature": 4,
    "corrosion_allowance": 5,
    "pipe_construction_type": 6,
    "external_design_pressure": 1,
}


def _expected_value_class(meta: dict) -> str:
    parameter_class = str(meta.get("parameter_class") or "").strip()
    dimension = str(meta.get("dimension") or "").strip()
    key = str(meta.get("key") or "").strip()
    if key in {"nominal_pipe_size", "outside_diameter", "inside_diameter"} or key.endswith("_pipe_size"):
        return "pipe_size"
    if parameter_class == "categorical" and dimension in _DESIGNATION_DIMENSIONS:
        return "material"
    if parameter_class in {"selection"}:
        return "selection"
    if parameter_class in {"physical_quantity", "geometric_quantity", "environmental_condition"}:
        return "quantity"
    if parameter_class in {"factor", "coefficient"}:
        return "quantity"
    return "selection"


def _allowed_units(meta: dict) -> list[str] | None:
    parameter_class = str(meta.get("parameter_class") or "").strip()
    dimension = str(meta.get("dimension") or "").strip()
    if parameter_class == "categorical":
        return None
    registry = get_unit_registry()
    allowed_ids = registry.allowed_units_for_parameter(
        param_meta=meta,
        quantity_dimension=dimension or None,
        is_designation=False,
    )
    units = [symbol_from_unit_id(unit_id) for unit_id in allowed_ids]
    return units or None


def _label(meta: dict, field: str) -> str:
    name = str(meta.get("name") or "").strip()
    if name:
        return name
    return field.replace("_", " ").title()


def build_question_spec(
    field: str,
    *,
    ask_policy: str = "ask_now",
    label_override: str | None = None,
    expected_value_class_override: str | None = None,
    priority_override: int | None = None,
) -> QuestionSpec:
    param_node_id = param_node_id_for_input(field)
    meta = load_parameter_node_metadata(param_node_id) or {"key": field}
    return QuestionSpec(
        field=field,
        label=label_override or _label(meta, field),
        reason_code=_REASON_CODES.get(field),
        expected_value_class=expected_value_class_override or _expected_value_class(meta),
        allowed_units=_allowed_units(meta),
        priority=priority_override if priority_override is not None else _PRIORITY.get(field, 50),
        ask_policy=ask_policy,
    )
