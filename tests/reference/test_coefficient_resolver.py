"""Coefficient resolver tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.coefficient_resolver import (
    compute_thick_wall_y,
    interpolate_by_temperature,
    lookup_quality_factor,
    lookup_y_coefficient,
    propose_coefficient_defaults,
)
from engine.reference.standards_paths import resolve_standard_pack


def _pack_root() -> Path:
    root = Path(__file__).resolve().parents[2]
    return resolve_standard_pack(root / "knowledge" / "standards", "asme_b31.3")


def test_interpolate_y_table_at_300f() -> None:
    rows = [
        {"design_temperature": 100, "coefficient_Y": 0.4},
        {"design_temperature": 700, "coefficient_Y": 0.5},
    ]
    value, _, interpolated = interpolate_by_temperature(
        rows,
        temperature_f=300.0,
        value_key="coefficient_Y",
        interpolate=True,
    )
    assert interpolated is True
    assert 0.4 < value < 0.5


def test_lookup_y_interpolation() -> None:
    pack = _pack_root()
    value, interpolated = lookup_y_coefficient(
        pack,
        design_temperature=150,
        design_temperature_unit="F",
    )
    assert 0.4 == value
    assert value == 0.4


def test_lookup_y_with_metallurgical_group() -> None:
    pack = _pack_root()
    value, _ = lookup_y_coefficient(
        pack,
        design_temperature=150,
        design_temperature_unit="F",
        metallurgical_group="ferritic_steels",
    )
    assert value == 0.4


def test_thick_wall_y_formula() -> None:
    y = compute_thick_wall_y(
        inside_diameter=200.0,
        outside_diameter=220.0,
        corrosion_allowance=1.0,
    )
    assert abs(y - (202.0 / 422.0)) < 1e-9


def test_lookup_quality_factor_a1b_seamless_and_forging() -> None:
    pack = _pack_root()
    e_seamless = lookup_quality_factor(pack, material="SA-106B", joint_category="seamless")
    e_forging = lookup_quality_factor(pack, material="A105", joint_category="forging")
    assert e_seamless == 1.0
    assert e_forging == 0.6


def test_lookup_quality_factor_a1b_a53_and_api_5l() -> None:
    pack = _pack_root()
    assert (
        lookup_quality_factor(pack, material="A53", joint_category="Electric resistance welded pipe")
        == 0.85
    )
    assert (
        lookup_quality_factor(
            pack,
            material="API 5L",
            joint_category="Electric fusion welded pipe, double butt seam",
        )
        == 0.95
    )


def test_lookup_quality_factor_resolves_material_catalog_alias() -> None:
    pack = _pack_root()
    assert lookup_quality_factor(pack, material="A106 Gr B", joint_category="seamless") == 1.0


def test_lookup_quality_factor_unknown_returns_none() -> None:
    pack = _pack_root()
    assert lookup_quality_factor(pack, material="UNKNOWN", joint_category="seamless") is None


def test_propose_coefficient_defaults_with_temperature() -> None:
    from models.input import EngineeringInput, InputSource

    pack = _pack_root()
    proposed = propose_coefficient_defaults(
        pack,
        existing_inputs={
            "design_temperature": EngineeringInput(
                "design_temperature", 200, "F", InputSource.USER
            ),
            "material": EngineeringInput("material", "SA-106B", "dimensionless", InputSource.USER),
            "joint_category": EngineeringInput(
                "joint_category", "seamless", "dimensionless", InputSource.USER
            ),
        },
    )
    assert proposed["temperature_coefficient_Y"][0] == 0.4
    assert proposed["weld_joint_efficiency"][0] == 1.0
