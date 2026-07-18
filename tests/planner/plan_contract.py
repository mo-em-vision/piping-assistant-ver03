"""Graph-derived requirement IDs for pipe-wall integration contract tests."""

from __future__ import annotations

from engine.planner.graph_requirements import (
    equation_requirement_id,
    lookup_requirement_id,
    requirement_id,
)
from engine.reference.parameter_keys import LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY

WELD_W_FIELD = "weld_joint_strength_reduction_factor_W"

PIPE_WALL_LOOKUP_IDS = (
    lookup_requirement_id("allowable_stress"),
    lookup_requirement_id("metallurgical_group"),
    lookup_requirement_id("temperature_coefficient_Y"),
    lookup_requirement_id(LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY),
    lookup_requirement_id(WELD_W_FIELD),
)

PIPE_WALL_TARGET_FIELD = "minimum_required_thickness"


def pipe_wall_equation_ids(
    *,
    target_field: str = PIPE_WALL_TARGET_FIELD,
) -> tuple[str, str]:
    empty: dict = {}
    return (
        equation_requirement_id("required_wall_thickness", empty),
        equation_requirement_id(target_field, empty, target_field=target_field),
    )


REQ_REQUIRED_WALL_THICKNESS, REQ_MINIMUM_REQUIRED_THICKNESS_EQ = pipe_wall_equation_ids()

PIPE_WALL_CONTRACT_REQUIREMENT_IDS = (
    requirement_id("straight_pipe_section"),
    requirement_id("pressure_design_case"),
    requirement_id("internal_design_gage_pressure"),
    "REQ-diameter_resolution",
    requirement_id("material_grade"),
    requirement_id("design_temperature"),
    requirement_id("corrosion_allowance"),
    requirement_id("pipe_construction_type"),
    *PIPE_WALL_LOOKUP_IDS,
    REQ_REQUIRED_WALL_THICKNESS,
    REQ_MINIMUM_REQUIRED_THICKNESS_EQ,
    "REQ-calculation_report",
)

LOOKUP_SOURCES = {
    lookup_requirement_id("allowable_stress"): "asme-b313-table-A-1",
    lookup_requirement_id("metallurgical_group"): "MAT-catalog",
    lookup_requirement_id("temperature_coefficient_Y"): "asme-b313-table-304-1-1-1",
    lookup_requirement_id(LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY): "asme-b313-table-A-3",
    lookup_requirement_id(WELD_W_FIELD): "asme-b313-table-302-3-5-1",
}

EQUATION_SOURCES = {
    REQ_REQUIRED_WALL_THICKNESS: "asme-b313-304-1-2-eq-3a",
    REQ_MINIMUM_REQUIRED_THICKNESS_EQ: "asme-b313-304-1-1-eq-2",
}
