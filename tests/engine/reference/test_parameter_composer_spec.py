"""Tests for PARAM-node-driven composer parameter specs."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.parameter_composer_spec import build_composer_parameter_spec
from engine.reference.standards_reader import StandardsReader


@pytest.fixture(scope="module")
def standards_root() -> Path:
    return Path(__file__).resolve().parents[3] / "knowledge" / "standards"


@pytest.fixture(scope="module")
def reader(standards_root: Path) -> StandardsReader:
    return StandardsReader(standards_root, standard="asme_b31.3")


def test_material_grade_spec_from_param_node(reader: StandardsReader) -> None:
    spec = build_composer_parameter_spec("material_grade", reader=reader)
    assert spec["type"] == "material"
    assert spec["label"] == "Material Grade"
    assert spec["units"] == []


def test_design_temperature_spec_includes_temperature_units(reader: StandardsReader) -> None:
    spec = build_composer_parameter_spec("design_temperature", reader=reader)
    assert spec["type"] == "number"
    assert spec["units"] == ["degC", "degF"]
    assert spec["default_unit"] == "degC"
    assert spec.get("validation", {}).get("min") == -273


def test_pressure_loading_spec_from_param_node(reader: StandardsReader) -> None:
    spec = build_composer_parameter_spec("pressure_loading", reader=reader)
    assert spec["type"] == "dropdown"
    assert {item["value"] for item in spec.get("options") or []} == {
        "internal_pressure",
        "external_pressure",
    }


def test_straight_pipe_section_spec_uses_checkbox(reader: StandardsReader) -> None:
    spec = build_composer_parameter_spec("straight_pipe_section", reader=reader)
    assert spec["type"] == "checkbox"
    assert spec.get("default_value") is True


def test_nominal_pipe_size_spec_uses_nps_default_unit(reader: StandardsReader) -> None:
    spec = build_composer_parameter_spec("nominal_pipe_size", reader=reader)
    assert spec["type"] == "dropdown"
    assert spec["default_unit"] == "NPS"


def test_weld_joint_efficiency_spec_has_bounded_validation(reader: StandardsReader) -> None:
    spec = build_composer_parameter_spec("weld_joint_efficiency", reader=reader)
    assert spec["type"] == "number"
    assert spec.get("validation") == {"min": 0, "max": 1}


def test_corrosion_allowance_spec_excludes_meter(reader: StandardsReader) -> None:
    spec = build_composer_parameter_spec("corrosion_allowance", reader=reader)
    assert spec["type"] == "number"
    assert spec["units"] == ["mm", "in"]
    assert spec["default_unit"] == "mm"
    assert "m" not in spec["units"]


def test_missing_param_node_raises_key_error() -> None:
    with pytest.raises(KeyError, match="No PARAM node metadata"):
        build_composer_parameter_spec("nonexistent_parameter_key")
