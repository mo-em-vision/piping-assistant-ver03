"""Pipe wall thickness workflow requirement templates and dependency graph."""

from __future__ import annotations

from engine.planner.question_spec_builder import build_question_spec
from engine.reference.parameter_keys import param_node_id_for_input
from models.engineering_plan import (
    ActivationCondition,
    CalculationGoal,
    PlanDependency,
    PlanRequirement,
    RequirementAlternative,
)

PIPE_WALL_WORKFLOW = "pipe_wall_thickness_design"

INTERNAL_PRESSURE_BRANCH_CONDITION = ActivationCondition(
    field="pressure_loading",
    operator="equals",
    value="internal_pressure",
)

_ALT_NPS_LOOKUP = "ALT-nps-lookup"
_ALT_DIRECT_OUTSIDE_DIAMETER = "ALT-direct-outside-diameter"

_GATE_REQUIREMENT_IDS = frozenset({"REQ-straight_pipe_section", "REQ-pressure_loading"})

ROOT_GOAL_ID = "GOAL-calculate-minimum-required-thickness"
ROOT_GOAL_KEY = "calculate-minimum-required-thickness"
ROOT_TARGET_PARAM = "PARAM-minimum-required-thickness"
ROOT_TARGET_FIELD = "minimum_required_thickness"

_USER_INPUT_FIELDS = (
    "internal_design_gage_pressure",
    "material_grade",
    "design_temperature",
    "corrosion_allowance",
)

_GATE_FIELDS = (
    "straight_pipe_section",
    "pressure_loading",
)

_COEFFICIENT_INPUT_FIELDS = ("pipe_construction_type",)

_LOOKUP_REQUIREMENTS: tuple[tuple[str, str, list[str], str | None], ...] = (
    (
        "REQ-allowable_stress_lookup",
        "allowable_stress",
        ["REQ-material_grade", "REQ-design_temperature"],
        None,
    ),
    (
        "REQ-weld_joint_efficiency_lookup",
        "weld_joint_efficiency",
        ["REQ-pipe_construction_type"],
        None,
    ),
    (
        "REQ-temperature_coefficient_Y_lookup",
        "temperature_coefficient_Y",
        ["REQ-metallurgical_group_lookup", "REQ-design_temperature"],
        None,
    ),
    (
        "REQ-weld_strength_reduction_factor_W_lookup",
        "weld_strength_reduction_factor_W",
        ["REQ-material_grade", "REQ-design_temperature"],
        None,
    ),
    (
        "REQ-metallurgical_group_lookup",
        "metallurgical_group",
        ["REQ-material_grade"],
        None,
    ),
)

_EQUATION_REQUIREMENTS: tuple[tuple[str, str, list[str]], ...] = (
    (
        "REQ-required_wall_thickness",
        "required_wall_thickness",
        [
            "REQ-internal_design_gage_pressure",
            "REQ-diameter_resolution",
            "REQ-allowable_stress_lookup",
            "REQ-weld_joint_efficiency_lookup",
            "REQ-temperature_coefficient_Y_lookup",
            "REQ-weld_strength_reduction_factor_W_lookup",
        ],
    ),
    (
        "REQ-minimum_required_thickness_eq",
        "minimum_required_thickness",
        ["REQ-required_wall_thickness", "REQ-corrosion_allowance"],
    ),
)


def req_id(field: str) -> str:
    return f"REQ-{field}"


def root_calculation_goal() -> CalculationGoal:
    return CalculationGoal(
        id=ROOT_GOAL_ID,
        key=ROOT_GOAL_KEY,
        title="Calculate minimum required pipe wall thickness",
        target_parameter=ROOT_TARGET_PARAM,
        target_field=ROOT_TARGET_FIELD,
        status="blocked",
        blocked_by=[],
        required_outputs=[
            "minimum_required_thickness",
            "required_wall_thickness",
            "calculation_report",
        ],
    )


def diameter_resolution_requirement() -> PlanRequirement:
    return PlanRequirement(
        id="REQ-diameter_resolution",
        field="outside_diameter",
        parameter_node_id=param_node_id_for_input("outside_diameter"),
        requirement_class="user_input",
        status="missing",
        phase="parameter_gathering",
        required_by=[ROOT_GOAL_ID],
        depends_on=[],
        alternatives=[
            RequirementAlternative(
                id="ALT-direct-outside-diameter",
                label="Provide outside diameter directly",
                fields=["outside_diameter"],
                resolves="outside_diameter",
                method="direct_input",
            ),
            RequirementAlternative(
                id="ALT-nps-lookup",
                label="Provide NPS and look up outside diameter",
                fields=["nominal_pipe_size"],
                resolves="outside_diameter",
                method="lookup",
            ),
        ],
        question_spec=build_question_spec(
            "diameter_input_mode",
            label_override="Pipe diameter",
            expected_value_class_override="pipe_size",
            priority_override=2,
        ),
    )


def nominal_pipe_size_requirement() -> PlanRequirement:
    return PlanRequirement(
        id=req_id("nominal_pipe_size"),
        field="nominal_pipe_size",
        parameter_node_id=param_node_id_for_input("nominal_pipe_size"),
        requirement_class="user_input",
        status="missing",
        phase="parameter_gathering",
        required_by=["REQ-diameter_resolution"],
        depends_on=[],
        question_spec=build_question_spec("nominal_pipe_size", ask_policy="ask_if_needed"),
        resolution={"method": "user_input", "output_field": "nominal_pipe_size"},
    )


def outside_diameter_lookup_requirement() -> PlanRequirement:
    return PlanRequirement(
        id="REQ-outside_diameter_lookup",
        field="outside_diameter",
        parameter_node_id=param_node_id_for_input("outside_diameter"),
        requirement_class="table_lookup",
        status="blocked",
        phase="parameter_gathering",
        required_by=["REQ-diameter_resolution"],
        depends_on=[req_id("nominal_pipe_size")],
        resolution={
            "method": "lookup",
            "source_node_id": "asme-b36.10-table",
            "output_field": "outside_diameter",
        },
    )


def user_input_requirement(field: str, *, phase: str, required_by: list[str]) -> PlanRequirement:
    return PlanRequirement(
        id=req_id(field),
        field=field,
        parameter_node_id=param_node_id_for_input(field),
        requirement_class="user_input",
        status="missing",
        phase=phase,
        required_by=required_by,
        depends_on=[],
        question_spec=build_question_spec(field),
        resolution={"method": "user_input", "output_field": field},
    )


def gate_requirement(field: str, *, phase: str) -> PlanRequirement:
    req_class = "branch_decision" if field == "pressure_loading" else "user_input"
    return PlanRequirement(
        id=req_id(field),
        field=field,
        parameter_node_id=param_node_id_for_input(field),
        requirement_class=req_class,
        status="missing",
        phase=phase,
        required_by=[ROOT_GOAL_ID],
        depends_on=[],
        question_spec=build_question_spec(field, priority_override=0),
        resolution={"method": "user_input", "output_field": field},
    )


def lookup_requirement(
    req_id_value: str,
    field: str,
    depends_on: list[str],
    *,
    source_node_id: str | None = None,
) -> PlanRequirement:
    resolution: dict[str, str] = {"method": "lookup", "output_field": field}
    if source_node_id:
        resolution["source_node_id"] = source_node_id
    return PlanRequirement(
        id=req_id_value,
        field=field,
        parameter_node_id=param_node_id_for_input(field),
        requirement_class="table_lookup",
        status="blocked",
        phase="coefficient_resolution",
        required_by=[ROOT_GOAL_ID],
        depends_on=depends_on,
        resolution=resolution,
    )


def equation_requirement(req_id_value: str, field: str, depends_on: list[str]) -> PlanRequirement:
    return PlanRequirement(
        id=req_id_value,
        field=field,
        parameter_node_id=param_node_id_for_input(field),
        requirement_class="equation_result",
        status="blocked",
        phase="equation_execution",
        required_by=[ROOT_GOAL_ID],
        depends_on=depends_on,
        resolution={"method": "equation", "output_field": field},
    )


def build_pipe_wall_requirements() -> dict[str, PlanRequirement]:
    requirements: dict[str, PlanRequirement] = {}

    for field in _GATE_FIELDS:
        phase = "expansion_assumptions" if field == "straight_pipe_section" else "path_decisions"
        requirements[req_id(field)] = gate_requirement(field, phase=phase)

    requirements[req_id("internal_design_gage_pressure")] = user_input_requirement(
        "internal_design_gage_pressure",
        phase="parameter_gathering",
        required_by=[ROOT_GOAL_ID],
    )

    requirements["REQ-diameter_resolution"] = diameter_resolution_requirement()
    requirements[req_id("nominal_pipe_size")] = nominal_pipe_size_requirement()
    requirements["REQ-outside_diameter_lookup"] = outside_diameter_lookup_requirement()

    for field in ("material_grade", "design_temperature"):
        requirements[req_id(field)] = user_input_requirement(
            field,
            phase="parameter_gathering",
            required_by=[ROOT_GOAL_ID],
        )

    requirements[req_id("corrosion_allowance")] = user_input_requirement(
        "corrosion_allowance",
        phase="parameter_gathering",
        required_by=[ROOT_GOAL_ID],
    )

    for field in _COEFFICIENT_INPUT_FIELDS:
        requirements[req_id(field)] = user_input_requirement(
            field,
            phase="coefficient_resolution",
            required_by=[ROOT_GOAL_ID],
        )

    for lookup_id, field, deps, source in _LOOKUP_REQUIREMENTS:
        requirements[lookup_id] = lookup_requirement(lookup_id, field, deps, source_node_id=source)

    for eq_id, field, deps in _EQUATION_REQUIREMENTS:
        requirements[eq_id] = equation_requirement(eq_id, field, deps)

    for requirement_id, req in requirements.items():
        if requirement_id in _GATE_REQUIREMENT_IDS:
            continue
        req.activation_condition = INTERNAL_PRESSURE_BRANCH_CONDITION

    return requirements


def build_pipe_wall_dependencies() -> list[PlanDependency]:
    edges: list[PlanDependency] = []

    def add(from_id: str, to_id: str, edge_type: str) -> None:
        edges.append(PlanDependency(from_id=from_id, to_id=to_id, type=edge_type))

    add("REQ-internal_design_gage_pressure", "REQ-required_wall_thickness", "equation_input")
    add("REQ-diameter_resolution", "REQ-required_wall_thickness", "equation_input")
    add("REQ-material_grade", "REQ-allowable_stress_lookup", "lookup_input")
    add("REQ-design_temperature", "REQ-allowable_stress_lookup", "lookup_input")
    add("REQ-allowable_stress_lookup", "REQ-required_wall_thickness", "equation_input")
    add("REQ-pipe_construction_type", "REQ-weld_joint_efficiency_lookup", "lookup_input")
    add("REQ-weld_joint_efficiency_lookup", "REQ-required_wall_thickness", "equation_input")
    add("REQ-material_grade", "REQ-metallurgical_group_lookup", "lookup_input")
    add("REQ-metallurgical_group_lookup", "REQ-temperature_coefficient_Y_lookup", "lookup_input")
    add("REQ-design_temperature", "REQ-temperature_coefficient_Y_lookup", "lookup_input")
    add("REQ-temperature_coefficient_Y_lookup", "REQ-required_wall_thickness", "equation_input")
    add("REQ-material_grade", "REQ-weld_strength_reduction_factor_W_lookup", "lookup_input")
    add("REQ-design_temperature", "REQ-weld_strength_reduction_factor_W_lookup", "lookup_input")
    add("REQ-weld_strength_reduction_factor_W_lookup", "REQ-required_wall_thickness", "equation_input")
    add("REQ-corrosion_allowance", "REQ-minimum_required_thickness_eq", "equation_input")
    add("REQ-required_wall_thickness", "REQ-minimum_required_thickness_eq", "equation_input")
    add(req_id("nominal_pipe_size"), "REQ-outside_diameter_lookup", "lookup_input")
    add("REQ-outside_diameter_lookup", "REQ-diameter_resolution", "resolves")
    add(_ALT_NPS_LOOKUP, req_id("nominal_pipe_size"), "activates")
    add(_ALT_NPS_LOOKUP, "REQ-outside_diameter_lookup", "activates")

    return edges


def root_blocked_by_for_gathering() -> list[str]:
    return [
        req_id("internal_design_gage_pressure"),
        "REQ-diameter_resolution",
        req_id("material_grade"),
        req_id("design_temperature"),
        req_id("pipe_construction_type"),
        req_id("corrosion_allowance"),
    ]
