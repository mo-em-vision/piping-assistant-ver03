"""Tests for lookup resolution inferred from graph lookup nodes."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.graph.lookup_parameter_resolution import (
    lookup_resolution_for_parameter,
    prerequisite_input_keys,
)
from engine.reference.parameter_keys import LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY
from engine.reference.standards_reader import StandardsReader


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_temperature_coefficient_y_infers_table_lookup_from_graph() -> None:
    reader = _reader()
    micro = GraphEngine()._micro_engine(reader)
    assert micro is not None

    resolution = lookup_resolution_for_parameter(micro.store, "PARAM-temperature-coefficient-Y")
    assert resolution is not None
    assert resolution["method"] == "table_lookup"
    assert "design_temperature" in resolution["keys"]
    assert "metallurgical_group" in resolution["keys"]
    conditionals = resolution.get("lookup_conditionals", {}).get("design_temperature", {})
    assert conditionals.get("min") == 900
    assert conditionals.get("max") == 1250


def test_weld_joint_efficiency_infers_table_lookup_from_graph() -> None:
    reader = _reader()
    micro = GraphEngine()._micro_engine(reader)
    assert micro is not None

    resolution = lookup_resolution_for_parameter(
        micro.store, "PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes"
    )
    assert resolution is not None
    assert resolution["method"] == "table_lookup"
    assert "material_grade" in resolution["keys"]
    assert "pipe_construction_type" in resolution["keys"]


def test_weld_strength_reduction_factor_w_infers_table_lookup_from_graph() -> None:
    reader = _reader()
    micro = GraphEngine()._micro_engine(reader)
    assert micro is not None

    resolution = lookup_resolution_for_parameter(
        micro.store, "PARAM-weld-strength-reduction-factor-W"
    )
    assert resolution is not None
    assert resolution["method"] == "table_lookup"
    assert "material_grade" in resolution["keys"]
    assert "design_temperature" in resolution["keys"]
    assert "pipe_construction_type" in resolution["keys"]


def test_required_user_inputs_do_not_include_lookup_derived_coefficients() -> None:
    reader = _reader()
    engine = GraphEngine()
    from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
    from tests.helpers.facts import facts_from_inputs

    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": internal_pressure_assumption(),
        },
        task_id="lookup-inputs-test",
    )
    missing = engine.required_user_inputs(
        "pipe_wall_thickness_design",
        reader,
        task_inputs=inputs,
    )
    assert "temperature_coefficient_Y" not in missing
    assert LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY not in missing
    assert "weld_joint_strength_reduction_factor_W" not in missing


def test_required_user_inputs_do_not_include_temperature_coefficient_y() -> None:
    reader = _reader()
    engine = GraphEngine()
    missing = engine.required_user_inputs(
        "pipe_wall_thickness_design",
        reader,
        task_inputs={},
    )
    assert "temperature_coefficient_Y" not in missing


def test_metallurgical_group_infers_material_catalog_resolution() -> None:
    reader = _reader()
    micro = GraphEngine()._micro_engine(reader)
    assert micro is not None

    from engine.graph.lookup_parameter_resolution import (
        catalog_resolution_for_parameter,
        parameter_resolution_for_parameter,
        prerequisite_input_keys,
    )

    resolution = catalog_resolution_for_parameter(micro.store, "PARAM-metallurgical-group")
    assert resolution is not None
    assert resolution["method"] == "material_catalog"
    assert resolution["keys"] == ["material_grade"]

    assert parameter_resolution_for_parameter(micro.store, "PARAM-metallurgical-group") == resolution
    assert prerequisite_input_keys(micro.store, "metallurgical_group") == ["material_grade"]


def test_prerequisite_input_keys_returns_lookup_keys_for_table_derived_parameters() -> None:
    reader = _reader()
    micro = GraphEngine()._micro_engine(reader)
    assert micro is not None

    from engine.graph.lookup_parameter_resolution import prerequisite_input_keys

    assert prerequisite_input_keys(micro.store, "allowable_stress") == [
        "material_grade",
        "design_temperature",
    ]
    assert prerequisite_input_keys(micro.store, LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY) == [
        "material_grade",
        "pipe_construction_type",
    ]
    assert prerequisite_input_keys(micro.store, "weld_joint_strength_reduction_factor_W") == [
        "material_grade",
        "design_temperature",
        "pipe_construction_type",
    ]
    assert "design_temperature" in prerequisite_input_keys(
        micro.store, "temperature_coefficient_Y"
    )


def test_required_user_inputs_do_not_include_metallurgical_group() -> None:
    reader = _reader()
    engine = GraphEngine()
    from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
    from tests.helpers.facts import facts_from_inputs

    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": internal_pressure_assumption(),
        },
        task_id="lookup-inputs-test",
    )
    missing = engine.required_user_inputs(
        "pipe_wall_thickness_design",
        reader,
        task_inputs=inputs,
    )
    assert "metallurgical_group" not in missing
    assert "material_grade" in missing
