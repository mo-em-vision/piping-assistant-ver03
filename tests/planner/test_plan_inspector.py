"""Tests for planner inspector summary helpers."""

from __future__ import annotations

from engine.planner.plan_inspector import dependency_ids_to_fields
from models.engineering_plan import PlanRequirement


def test_dependency_ids_to_fields_resolves_lookup_chain() -> None:
    requirements = {
        "REQ-material_grade": PlanRequirement(
            id="REQ-material_grade",
            field="material_grade",
            parameter_node_id="PARAM-material-grade",
            requirement_class="user_input",
            status="missing",
            phase="parameter_gathering",
        ),
        "REQ-metallurgical_group_lookup": PlanRequirement(
            id="REQ-metallurgical_group_lookup",
            field="metallurgical_group",
            parameter_node_id="PARAM-metallurgical-group",
            requirement_class="table_lookup",
            status="blocked",
            phase="coefficient_resolution",
            depends_on=["REQ-material_grade"],
        ),
        "REQ-design_temperature": PlanRequirement(
            id="REQ-design_temperature",
            field="design_temperature",
            parameter_node_id="PARAM-design-temperature",
            requirement_class="user_input",
            status="missing",
            phase="parameter_gathering",
        ),
        "REQ-temperature_coefficient_Y_lookup": PlanRequirement(
            id="REQ-temperature_coefficient_Y_lookup",
            field="temperature_coefficient_Y",
            parameter_node_id="PARAM-temperature-coefficient-Y",
            requirement_class="table_lookup",
            status="blocked",
            phase="coefficient_resolution",
            depends_on=["REQ-metallurgical_group_lookup", "REQ-design_temperature"],
        ),
    }

    assert dependency_ids_to_fields(
        ["REQ-metallurgical_group_lookup", "REQ-design_temperature"],
        requirements,
    ) == ["metallurgical_group", "design_temperature"]
