"""Tests for graph-native unit conversion."""

from __future__ import annotations

import pytest

from engine.units.unit_resolver import UnitResolver, reset_unit_resolver


@pytest.fixture(autouse=True)
def _fresh_resolver() -> None:
    reset_unit_resolver()
    yield
    reset_unit_resolver()


@pytest.fixture
def resolver() -> UnitResolver:
    return UnitResolver.default()


def test_psi_to_pa(resolver: UnitResolver) -> None:
    value, unit = resolver.convert_value(1.0, "psi", "Pa")
    assert unit == "Pa"
    assert value == pytest.approx(6894.757293168)


def test_bar_to_pa(resolver: UnitResolver) -> None:
    value, unit = resolver.convert_value(1.0, "bar", "UNIT-Pa")
    assert unit == "Pa"
    assert value == pytest.approx(100_000.0)


def test_psi_to_mpa_multi_hop(resolver: UnitResolver) -> None:
    value, unit = resolver.convert_value(1.0, "psi", "MPa")
    assert unit == "MPa"
    assert value == pytest.approx(0.006894757293168)


def test_inch_to_mm(resolver: UnitResolver) -> None:
    value, unit = resolver.convert_value(1.0, "in", "mm")
    assert unit == "mm"
    assert value == pytest.approx(25.4)


def test_meter_to_mm(resolver: UnitResolver) -> None:
    value, unit = resolver.convert_value(1.0, "m", "mm")
    assert unit == "mm"
    assert value == pytest.approx(1000.0)


def test_fahrenheit_to_kelvin(resolver: UnitResolver) -> None:
    value, unit = resolver.convert_value(32.0, "f", "K")
    assert unit == "K"
    assert value == pytest.approx(273.15, rel=1e-4)


def test_invalid_dimension_rejected(resolver: UnitResolver) -> None:
    with pytest.raises(ValueError, match="Incompatible dimensions"):
        resolver.convert_value(100.0, "psi", "mm")


def test_unit_manager_delegates_to_resolver() -> None:
    from engine.executor.unit_manager import convert_to_si

    value, unit = convert_to_si(500, "psi")
    assert unit == "Pa"
    assert value == pytest.approx(500 * 6894.757293168)


def test_parameter_metadata_sets_canonical_unit() -> None:
    from engine.reference.parameter_metadata import prepare_parameter_metadata

    meta = prepare_parameter_metadata({"unit": "Pa", "input_id": "design_pressure"})
    assert meta["canonical_unit"] == "UNIT-Pa"
    assert meta["unit"] == "Pa"


def test_convert_to_canonical_si_stress_dimension(resolver: UnitResolver) -> None:
    value, unit = resolver.convert_to_canonical_si(1.0, "psi", dimension="stress")
    assert unit == "Pa"
    assert value == pytest.approx(6894.757293168)


def test_unit_pack_compiles() -> None:
    from engine.graph.graph_builder import GraphBuilder
    from pathlib import Path

    pack_root = Path(__file__).resolve().parents[2] / "knowledge" / "global" / "units"
    graph = GraphBuilder(pack_root).build()
    assert "UNIT-Pa" in graph.nodes
    assert "UNIT-psi" in graph.nodes
    converts = [edge for edge in graph.edges if edge.edge_type == "converts_to"]
    assert any(edge.from_id == "UNIT-psi" and edge.to_id == "UNIT-Pa" for edge in converts)
    factor = next(
        edge.metadata.get("factor")
        for edge in converts
        if edge.from_id == "UNIT-psi" and edge.to_id == "UNIT-Pa"
    )
    assert factor == pytest.approx(6894.757293168)


def test_physical_dimensions_pack_compiles() -> None:
    from engine.graph.graph_builder import GraphBuilder
    from pathlib import Path

    pack_root = Path(__file__).resolve().parents[2] / "knowledge" / "global" / "dimensions"
    graph = GraphBuilder(pack_root).build()
    assert "DIM-pressure" in graph.nodes
    assert "DIM-velocity" in graph.nodes
    pressure = graph.nodes["DIM-pressure"]
    assert set(pressure.metadata.get("references", [])) == {
        "UNIT-Pa",
        "UNIT-MPa",
        "UNIT-psi",
        "UNIT-bar",
    }
    assert pressure.metadata.get("canonical_unit") == "UNIT-Pa"
