"""Tests for deterministic chat input extraction."""

from __future__ import annotations

from ai.input_extractor import extract_engineering_inputs
from engine.graph.node_interaction import InteractionMode, NodeInteractionSpec
from models.fact import fact_from_user_submission, fact_scalar_value, fact_unit
from models.input import InputStatus, proposed_default_input

USER_MESSAGE = "material ASTM A106, Temperature: 85 Celcius, Pressure: 4 inch"


def test_extracts_material_and_temperature_from_user_message() -> None:
    result = extract_engineering_inputs(USER_MESSAGE)

    assert "material_grade" in result.extracted
    assert fact_scalar_value(result.extracted["material_grade"]) == "astm_a106_gr_b"
    assert "design_temperature" in result.extracted
    assert fact_scalar_value(result.extracted["design_temperature"]) == 85.0
    assert fact_unit(result.extracted["design_temperature"]) in {"C", "degC"}


def test_rejects_mislabeled_pressure_with_length_unit() -> None:
    result = extract_engineering_inputs(USER_MESSAGE)

    assert "design_pressure" not in result.extracted
    assert len(result.rejected) == 1
    rejection = result.rejected[0]
    assert rejection.input_id == "design_pressure"
    assert "4" in rejection.raw_value
    assert "inch" in rejection.reason.lower()


def test_diameter_still_missing_when_pressure_mislabeled() -> None:
    result = extract_engineering_inputs(USER_MESSAGE)

    assert "outside_diameter" not in result.extracted


def test_extracts_valid_pressure_and_diameter() -> None:
    result = extract_engineering_inputs(
        "design pressure 500 psi, outside diameter 10 inch, material SA-106B, temp 200 F"
    )

    assert result.extracted["design_pressure"].value == 500.0
    assert result.extracted["design_pressure"].unit == "psi"
    assert result.extracted["outside_diameter"].value == 10.0
    assert result.extracted["outside_diameter"].unit == "in"
    assert result.extracted["d_input_mode"].value == "direct_od"
    assert not result.rejected


def test_extracts_nps_for_b36_lookup() -> None:
    result = extract_engineering_inputs("NPS 2, design pressure 500 psi, material SA-106B, temp 200 F")

    assert fact_scalar_value(result.extracted["nominal_pipe_size"]) == "2"
    assert result.extracted["nominal_pipe_size"].original_unit == "NPS"
    assert fact_scalar_value(result.extracted["d_input_mode"]) == "nps_lookup"
    assert "outside_diameter" not in result.extracted


def test_rejects_pressure_without_recognized_unit() -> None:
    result = extract_engineering_inputs("pressure: 500 unknownunit")

    assert "design_pressure" not in result.extracted
    assert any(r.input_id == "design_pressure" for r in result.rejected)


def test_extracts_internal_pressure_design_case() -> None:
    result = extract_engineering_inputs("internal pressure")

    assert result.extracted["pressure_design_case"].value == "internal_pressure"
    assert result.extracted["pressure_design_case"].status == InputStatus.CONFIRMED


def test_extracts_external_pressure_design_case() -> None:
    result = extract_engineering_inputs("external pressure")

    assert result.extracted["pressure_design_case"].value == "external_pressure"
    assert result.extracted["pressure_design_case"].status == InputStatus.CONFIRMED


def test_extracts_short_internal_reply() -> None:
    result = extract_engineering_inputs("internal")

    assert result.extracted["pressure_design_case"].value == "internal_pressure"


def test_extracts_numbered_straight_pipe_yes() -> None:
    result = extract_engineering_inputs(
        "1",
        allowed_fields=frozenset({"straight_pipe_section"}),
    )

    assert result.extracted["straight_pipe_section"].value is True


def test_extracts_numbered_pressure_design_case_choice() -> None:
    result = extract_engineering_inputs("1")

    assert result.extracted["pressure_design_case"].value == "internal_pressure"


def test_extracts_option_two_for_external_pressure() -> None:
    result = extract_engineering_inputs("option 2")

    assert result.extracted["pressure_design_case"].value == "external_pressure"


def test_design_pressure_does_not_set_pressure_design_case() -> None:
    result = extract_engineering_inputs("design pressure 500 psi")

    assert "pressure_design_case" not in result.extracted
    assert result.extracted["design_pressure"].value == 500.0


def test_confirm_prioritizes_joint_category_over_coefficient_defaults() -> None:
    joint_spec = NodeInteractionSpec(
        variable="joint_category",
        mode=InteractionMode.DECISION,
        node_id="304.1.2-a",
        required=True,
        options=("seamless", "erw"),
        default="seamless",
        confirmation_required=True,
    )
    e_spec = NodeInteractionSpec(
        variable="weld_joint_efficiency",
        mode=InteractionMode.VALUE_RESOLUTION,
        node_id="304.1.2-a",
        default=1.0,
        confirmation_required=True,
        unit="dimensionless",
    )
    existing = {
        "joint_category": proposed_default_input("joint_category", "seamless"),
        "weld_joint_efficiency": proposed_default_input("weld_joint_efficiency", 1.0),
    }
    result = extract_engineering_inputs(
        "confirm",
        pending_interactions=[joint_spec],
        pending_value_confirmations=[e_spec],
        existing_inputs=existing,
        allowed_fields=frozenset({"joint_category", "weld_joint_efficiency"}),
    )

    assert result.extracted["joint_category"].status == InputStatus.CONFIRMED
    assert "weld_joint_efficiency" not in result.extracted


def test_extracts_symbol_labeled_pressure_and_diameter() -> None:
    result = extract_engineering_inputs("P: 8 bar, D: 4inch")

    assert result.extracted["design_pressure"].value == 8.0
    assert result.extracted["design_pressure"].unit == "bar"
    assert result.extracted["outside_diameter"].value == 4.0
    assert result.extracted["outside_diameter"].unit == "in"
    assert result.extracted["d_input_mode"].value == "direct_od"
    assert not result.rejected


def test_rejects_symbol_labeled_pressure_with_length_unit() -> None:
    result = extract_engineering_inputs("P: 4 inch")

    assert "design_pressure" not in result.extracted
    assert any(r.input_id == "design_pressure" for r in result.rejected)


def test_symbol_labeled_e_override_on_proposed_default() -> None:
    existing = {
        "weld_joint_efficiency": proposed_default_input("weld_joint_efficiency", 1.0),
    }
    result = extract_engineering_inputs(
        "E: 0.85",
        existing_inputs=existing,
        allowed_fields=frozenset({"weld_joint_efficiency"}),
    )

    assert result.extracted["weld_joint_efficiency"].value == 0.85
    assert result.extracted["weld_joint_efficiency"].status == InputStatus.USER_OVERRIDE
