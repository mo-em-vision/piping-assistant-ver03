"""Nomenclature resolver tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.node_interaction import load_node_interactions, question_for_interaction
from engine.reference.nomenclature_resolver import (
    enrich_input_spec,
    enrich_output_spec,
    load_nomenclature,
    resolve_dimension_input_spec,
    resolve_dimension_output_spec,
    resolve_input_spec,
    resolve_material_input_spec,
    task_input_key,
)
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_load_nomenclature_c_defaults(reader: StandardsReader) -> None:
    nomenclature = load_nomenclature(reader, "B313-304.1.1")
    entry = nomenclature["c"]
    assert entry.input_id == "corrosion_allowance"
    assert entry.defaults
    assert entry.defaults[0].value == 0.5
    assert entry.defaults[0].unit == "mm"
    assert "tolerance" in (entry.defaults[0].condition or "")


def test_load_nomenclature_d_b36_reference(reader: StandardsReader) -> None:
    nomenclature = load_nomenclature(reader, "B313-304.1.1")
    entry = nomenclature["D"]
    assert entry.input_id == "outside_diameter"
    assert any(
        ref.get("standard") == "asme_b36.10" for ref in entry.references
    )


def test_resolve_dimension_input_spec_merges_dim_temperature() -> None:
    merged = resolve_dimension_input_spec(
        {
            "id": "design_temperature",
            "references": ["DIM-temperature"],
            "required": True,
        }
    )
    assert merged["dimension"] == "temperature"
    assert merged["canonical_unit"] == "UNIT-K"
    assert merged["allowed_units"] == ["UNIT-K", "UNIT-degC", "UNIT-degF"]


def test_resolve_dimension_input_spec_applies_display_name() -> None:
    merged = resolve_dimension_input_spec(
        {
            "id": "temperature",
            "references": ["DIM-temperature"],
            "display_name": "Metal Temperature",
            "task_input_id": "design_temperature",
            "required": True,
        }
    )
    assert merged["name"] == "Metal Temperature"
    assert merged["description"] == "Metal Temperature"
    assert merged["dimension"] == "temperature"


def test_resolve_dimension_output_spec_merges_dim_pressure() -> None:
    merged = resolve_dimension_output_spec(
        {
            "id": "allowable_stress",
            "symbol": "S",
            "references": ["DIM-pressure"],
            "canonical_unit": "UNIT-MPa",
            "type": "quantity",
        }
    )
    assert merged["dimension"] == "pressure"
    assert merged["canonical_unit"] == "UNIT-MPa"
    assert merged["allowed_units"] == ["UNIT-Pa", "UNIT-MPa", "UNIT-psi", "UNIT-bar"]


def test_enrich_output_spec_delegates_to_dimension_resolver() -> None:
    merged = enrich_output_spec(
        {
            "id": "allowable_stress",
            "symbol": "S",
            "references": ["DIM-pressure"],
            "type": "quantity",
        }
    )
    assert merged["dimension"] == "pressure"
    assert merged["canonical_unit"] == "UNIT-Pa"


def test_resolve_material_input_spec_merges_mat_catalog() -> None:
    merged = resolve_material_input_spec(
        {
            "id": "material",
            "references": ["MAT-catalog"],
            "required": True,
        }
    )
    assert merged["unit"] == "dimensionless"
    assert merged["canonical_unit"] == "UNIT-dimensionless"


def test_enrich_input_spec_bridges_task_input_id() -> None:
    merged = enrich_input_spec(
        {
            "id": "temperature",
            "references": ["DIM-temperature"],
            "task_input_id": "design_temperature",
            "required": True,
        }
    )
    assert merged["binds_to"] == "design_temperature"
    assert merged["dimension"] == "temperature"
    assert task_input_key(merged) == "design_temperature"


def test_resolve_input_spec_merges_nomenclature_default(reader: StandardsReader) -> None:
    nomenclature = load_nomenclature(reader, "B313-304.1.1")
    merged = resolve_input_spec(
        {
            "id": "corrosion_allowance",
            "name": "c",
            "source": "default",
            "requires_confirmation": True,
        },
        nomenclature,
    )
    assert merged["default"] == 0.5
    assert merged.get("default_condition")


def test_corrosion_allowance_question_includes_condition(reader: StandardsReader) -> None:
    record = reader.load("B313-304.1.2")
    specs = load_node_interactions(record, reader)
    corrosion = next(s for s in specs if s.variable == "corrosion_allowance")
    question = question_for_interaction(corrosion)
    assert "0.5" in question
    assert "machined" in question.lower()
