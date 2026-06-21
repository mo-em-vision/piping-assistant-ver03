"""Nomenclature resolver tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.node_interaction import load_node_interactions, question_for_interaction
from engine.reference.nomenclature_resolver import (
    load_nomenclature,
    resolve_input_spec,
)
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "standards", standard="asme_b31.3")


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
