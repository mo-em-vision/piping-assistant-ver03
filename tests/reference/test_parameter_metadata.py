"""Tests for parameter node metadata normalization."""

from __future__ import annotations

from engine.reference.parameter_metadata import parameter_defined_in, prepare_parameter_metadata


def test_prepare_parameter_metadata_maps_canonical_symbol_and_name() -> None:
    meta = prepare_parameter_metadata(
        {
            "key": "internal_design_gage_pressure",
            "canonical_symbol": "P",
            "name": "Internal Design Gage Pressure",
            "introduced_by": ["asme-b313-304-1-1-b"],
        }
    )
    assert meta["symbol"] == "P"
    assert meta["title"] == "Internal Design Gage Pressure"
    assert parameter_defined_in(meta) == ("asme-b313-304-1-1-b",)


def test_parameter_defined_in_reads_introduced_by() -> None:
    meta = {"introduced_by": ["304.1.2-a", "304.1.1-b"]}
    assert parameter_defined_in(meta) == ("304.1.2-a", "304.1.1-b")


def test_prepare_parameter_metadata_resolves_unit_from_dimension() -> None:
    meta = prepare_parameter_metadata(
        {
            "key": "internal_design_gage_pressure",
            "dimension": "DIM-pressure",
            "edges": [{"type": "has_dimension", "target": "DIM-pressure"}],
        }
    )
    assert meta["canonical_unit"] == "UNIT-Pa"
    assert meta["unit"] == "Pa"
    assert meta["allowed_units"]


def test_prepare_parameter_metadata_merges_nested_metadata_block() -> None:
    meta = prepare_parameter_metadata(
        {
            "key": "design_temperature",
            "dimension": "DIM-temperature",
            "metadata": {
                "canonical_unit": "UNIT-degC",
                "allowed_units": ["UNIT-degC", "UNIT-degF"],
            },
        }
    )
    assert meta["canonical_unit"] == "UNIT-degC"
    assert meta["unit"] == "degC"
