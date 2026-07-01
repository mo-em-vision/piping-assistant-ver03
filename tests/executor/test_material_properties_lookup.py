"""ASTM material properties lookup tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.material_properties_lookup import MaterialPropertiesLookup


def _a106() -> MaterialPropertiesLookup:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    return MaterialPropertiesLookup(root, standard="astm_a106")


def _a312() -> MaterialPropertiesLookup:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    return MaterialPropertiesLookup(root, standard="astm_a312")


def test_a106_grade_b_room_temperature_yield() -> None:
    result = _a106().lookup("SA-106B")
    assert result.grade == "A106 Gr B"
    assert result.mechanical.yield_strength_min_ksi == pytest.approx(35)
    assert result.mechanical.tensile_strength_min_ksi == pytest.approx(60)
    assert result.mechanical.elongation_min_percent == pytest.approx(30)


def test_a106_grade_b_elevated_temperature() -> None:
    result = _a106().lookup("A106B", test_temperature_f=400)
    assert result.mechanical.test_temperature_f == pytest.approx(400)
    assert result.mechanical.yield_strength_min_ksi == pytest.approx(29)


def test_a106_grade_a_chemical_limits() -> None:
    result = _a106().lookup("A106 Gr A")
    carbon = result.chemical_composition["limits"]["carbon"]
    assert carbon["max"] == pytest.approx(0.25)


def test_a312_tp316l_properties() -> None:
    result = _a312().lookup("316L")
    assert result.grade == "TP316L"
    assert result.mechanical.yield_strength_min_ksi == pytest.approx(25)
    assert result.mechanical.tensile_strength_min_ksi == pytest.approx(70)
    moly = result.chemical_composition["limits"]["molybdenum"]
    assert moly["min"] == pytest.approx(2.0)
    assert moly["max"] == pytest.approx(3.0)


def test_a312_tp304_alias() -> None:
    result = _a312().lookup("SS304")
    assert result.grade == "TP304"
    assert result.physical_properties["density_kg_m3"] == 8000


def test_unknown_grade_raises() -> None:
    with pytest.raises(ValueError, match="Material grade not found"):
        _a312().lookup("TP999")
