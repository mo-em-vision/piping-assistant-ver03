"""Tests for graph-backed unit registry (Phase 6)."""

from __future__ import annotations

import pytest

from engine.units.unit_registry import UnitRegistry, get_unit_registry, reset_unit_registry
from engine.units.unit_resolver import reset_unit_resolver


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    reset_unit_resolver()
    reset_unit_registry()
    yield
    reset_unit_resolver()
    reset_unit_registry()


@pytest.fixture
def registry() -> UnitRegistry:
    return UnitRegistry()


def test_units_for_pressure_dimension(registry: UnitRegistry) -> None:
    units = set(registry.units_for_dimension("pressure"))
    assert units == {"UNIT-Pa", "UNIT-psi", "UNIT-bar", "UNIT-MPa"}


def test_stress_aliases_to_pressure_units(registry: UnitRegistry) -> None:
    assert set(registry.units_for_dimension("stress")) == set(
        registry.units_for_dimension("pressure")
    )


def test_units_for_length_dimension(registry: UnitRegistry) -> None:
    units = set(registry.units_for_dimension("length"))
    assert units == {"UNIT-mm", "UNIT-m", "UNIT-in"}


def test_designation_parameter_only_dimensionless(registry: UnitRegistry) -> None:
    allowed = registry.allowed_units_for_parameter(
        param_meta={"canonical_unit": "UNIT-dimensionless"},
        quantity_dimension=None,
        is_designation=True,
    )
    assert allowed == ("UNIT-dimensionless",)


def test_explicit_allowed_units_on_parameter(registry: UnitRegistry) -> None:
    allowed = registry.allowed_units_for_parameter(
        param_meta={"allowed_units": ["UNIT-psi", "Pa"]},
        quantity_dimension="pressure",
        is_designation=False,
    )
    assert set(allowed) == {"UNIT-psi", "UNIT-Pa"}


def test_default_allowed_units_from_quantity_dimension(registry: UnitRegistry) -> None:
    allowed = registry.allowed_units_for_parameter(
        param_meta={"canonical_unit": "UNIT-Pa"},
        quantity_dimension="pressure",
        is_designation=False,
    )
    assert "UNIT-psi" in allowed
    assert "UNIT-Pa" in allowed


def test_resolve_allowed_unit_symbols(registry: UnitRegistry) -> None:
    symbols = registry.resolve_allowed_unit_symbols(
        param_meta={"canonical_unit": "UNIT-Pa"},
        quantity_dimension="pressure",
        is_designation=False,
    )
    assert "pa" in symbols
    assert "psi" in symbols


def test_get_unit_registry_singleton() -> None:
    assert get_unit_registry() is get_unit_registry()


def test_normalize_allowed_units_helper() -> None:
    from engine.reference.parameter_metadata import normalize_allowed_units

    assert normalize_allowed_units({"allowed_units": ["psi", "UNIT-Pa"]}) == [
        "UNIT-psi",
        "UNIT-Pa",
    ]
