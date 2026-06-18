"""Tests for deterministic chat input extraction."""

from __future__ import annotations

from ai.input_extractor import extract_pipe_wall_thickness_inputs

USER_MESSAGE = "material ASTM A106, Temperature: 85 Celcius, Pressure: 4 inch"


def test_extracts_material_and_temperature_from_user_message() -> None:
    result = extract_pipe_wall_thickness_inputs(USER_MESSAGE)

    assert "material" in result.extracted
    assert result.extracted["material"].value == "SA-106B"
    assert "design_temperature" in result.extracted
    assert result.extracted["design_temperature"].value == 85.0
    assert result.extracted["design_temperature"].unit == "C"


def test_rejects_mislabeled_pressure_with_length_unit() -> None:
    result = extract_pipe_wall_thickness_inputs(USER_MESSAGE)

    assert "design_pressure" not in result.extracted
    assert len(result.rejected) == 1
    rejection = result.rejected[0]
    assert rejection.input_id == "design_pressure"
    assert "4" in rejection.raw_value
    assert "inch" in rejection.reason.lower()


def test_diameter_still_missing_when_pressure_mislabeled() -> None:
    result = extract_pipe_wall_thickness_inputs(USER_MESSAGE)

    assert "outside_diameter" not in result.extracted


def test_extracts_valid_pressure_and_diameter() -> None:
    result = extract_pipe_wall_thickness_inputs(
        "design pressure 500 psi, outside diameter 10 inch, material SA-106B, temp 200 F"
    )

    assert result.extracted["design_pressure"].value == 500.0
    assert result.extracted["design_pressure"].unit == "psi"
    assert result.extracted["outside_diameter"].value == 10.0
    assert result.extracted["outside_diameter"].unit == "in"
    assert not result.rejected


def test_rejects_pressure_without_recognized_unit() -> None:
    result = extract_pipe_wall_thickness_inputs("pressure: 500 unknownunit")

    assert "design_pressure" not in result.extracted
    assert any(r.input_id == "design_pressure" for r in result.rejected)
