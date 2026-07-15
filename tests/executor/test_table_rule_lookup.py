"""Tests for v2 table rule lookup execution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.lookup_engine import LookupEngine
from engine.executor.lookup_rule_schema import load_table_lookup_rules
from engine.executor.table_rule_lookup import execute_pipe_dimensions_rule, execute_table_rule_lookup
from engine.reference.material_ids import ASTM_A106_GR_B, ASTM_A351
from engine.reference.standards_paths import resolve_standard_pack


def _standards_root() -> Path:
    return Path(__file__).resolve().parents[2] / "knowledge" / "standards"


def _lookup_engine() -> LookupEngine:
    pack_root = resolve_standard_pack(_standards_root(), "asme_b31.3")
    return LookupEngine(pack_root)


def test_b3610_table_yaml_exposes_v2_lookup_rules() -> None:
    rules = load_table_lookup_rules("B3610-table-2-1", standards_root=_standards_root())
    assert rules["by_nps"]["strategy"] == "pipe_nps"
    assert rules["by_nps"]["outputs"]["outside_diameter"]["column"] == "outside_diameter_mm"


def test_a1_table_yaml_exposes_v2_lookup_rules() -> None:
    rules = load_table_lookup_rules("asme-b313-table-A-1", standards_root=_standards_root())
    assert rules["by_material_temperature"]["strategy"] == "material_temperature"


def test_execute_rule_lookup_by_nps_resolves_outside_diameter() -> None:
    result = _lookup_engine().execute_rule_lookup(
        table_ref="B3610-table-2-1",
        rule="by_nps",
        inputs={"nominal_pipe_size": "4"},
        returns=[{"parameter": "PARAM-outside-diameter", "symbol": "D"}],
    )
    assert result.outputs["outside_diameter"] == pytest.approx(114.3)
    assert result.outputs["D"] == pytest.approx(114.3)
    assert result.meta["strategy"] == "pipe_nps"


def test_execute_rule_lookup_by_nps_schedule_resolves_wall_thickness() -> None:
    result = _lookup_engine().execute_rule_lookup(
        table_ref="B3610-table-2-1",
        rule="by_nps_schedule",
        inputs={"nominal_pipe_size": "2", "pipe_schedule": "40"},
        returns=[{"parameter": "PARAM-actual-wall-thickness", "symbol": "t_actual"}],
    )
    assert result.outputs["actual_wall_thickness"] == pytest.approx(3.91, rel=1e-2)
    assert result.outputs["t_actual"] == pytest.approx(3.91, rel=1e-2)


def test_execute_rule_lookup_a1_resolves_allowable_stress() -> None:
    result = _lookup_engine().execute_rule_lookup(
        table_ref="asme-b313-table-A-1",
        rule="by_material_temperature",
        inputs={"material_grade": "SA-106B", "design_temperature": 200, "design_temperature_unit": "F"},
        returns=[{"parameter": "PARAM-allowable-stress", "symbol": "S"}],
    )
    assert result.outputs["allowable_stress"] == pytest.approx(193_000_000.0)
    assert result.outputs["S"] == pytest.approx(193_000_000.0)
    assert result.meta["interpolated"] is False


def test_execute_rule_lookup_a1_interpolates_temperature() -> None:
    result = _lookup_engine().execute_rule_lookup(
        table_ref="asme-b313-table-A-1",
        rule="by_material_temperature",
        inputs={"material_grade": "A106-B", "design_temperature": 150, "design_temperature_unit": "F"},
        returns=[{"parameter": "PARAM-allowable-stress", "symbol": "S"}],
    )
    stress = result.outputs["allowable_stress"]
    assert 193_000_000.0 < stress < 207_000_000.0
    assert result.meta["interpolated"] is True


def test_execute_rule_lookup_y_coefficient_by_material_group() -> None:
    result = _lookup_engine().execute_rule_lookup(
        table_ref="asme-b313-table-304-1-1-1",
        rule="by_material_group_temperature",
        inputs={
            "design_temperature": 1000.0,
            "design_temperature_unit": "F",
            "metallurgical_group": "ferritic_steels",
        },
        returns=[{"parameter": "PARAM-temperature-coefficient-Y", "symbol": "Y"}],
    )
    assert result.outputs["temperature_coefficient_Y"] == pytest.approx(0.7)
    assert result.outputs["Y"] == pytest.approx(0.7)


def test_execute_rule_lookup_a3_resolves_quality_factor() -> None:
    result = _lookup_engine().execute_rule_lookup(
        table_ref="asme-b313-table-A-3",
        rule="by_material_joint_category",
        inputs={
            "material_grade": ASTM_A106_GR_B,
            "pipe_construction_type": "Seamless pipe",
        },
        returns=[
            {
                "parameter": "PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes",
                "symbol": "E_j",
            }
        ],
    )
    assert result.outputs["basic_quality_factor"] == pytest.approx(1.0)
    assert result.outputs["E_j"] == pytest.approx(1.0)


def test_execute_rule_lookup_a2_resolves_casting_quality_factor() -> None:
    result = _lookup_engine().execute_rule_lookup(
        table_ref="asme-b313-table-A-2",
        rule="by_material",
        inputs={"material_grade": ASTM_A351},
        returns=[{"parameter": "PARAM-basic-casting-quality-factor", "symbol": "E_c"}],
    )
    assert result.outputs["basic_casting_quality_factor"] == pytest.approx(0.8)
    assert result.outputs["E_c"] == pytest.approx(0.8)


def test_w_table_empty_rows_errors_without_default() -> None:
    with pytest.raises(ValueError, match="Material not found|No rows for material"):
        _lookup_engine().execute_rule_lookup(
            table_ref="asme-b313-table-302-3-5-1",
            rule="by_material_construction_temperature",
            inputs={
                "material_grade": ASTM_A106_GR_B,
                "pipe_construction_type": "Seamless pipe",
                "design_temperature": 200,
                "design_temperature_unit": "F",
            },
        )


def test_missing_rule_is_rejected() -> None:
    pack_root = resolve_standard_pack(_standards_root(), "asme_b31.3")
    with pytest.raises(ValueError, match="lookup.rule is required"):
        execute_table_rule_lookup(
            standards_pack_root=pack_root,
            table_ref="asme-b313-table-A-1",
            rule="",
            inputs={},
        )


def test_legacy_pipe_rule_alias_still_works() -> None:
    result = execute_pipe_dimensions_rule(
        standards_root=_standards_root(),
        rule="pipe_dimensions_nps_schedule",
        inputs={"nominal_pipe_size": "2", "pipe_schedule": "40"},
    )
    assert result.outputs["actual_wall_thickness"] == pytest.approx(3.91, rel=1e-2)
