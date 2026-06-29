"""Canonical node type normalization tests."""

from __future__ import annotations

from engine.reference.node_types import (
    is_designation_node,
    is_lookup_node,
    is_quantity_node,
    is_section_node,
    is_ui_parameter,
    normalize_node_metadata,
)


def test_assumption_normalizes_to_parameter() -> None:
    meta = {"field": "straight_pipe_section", "required_for_expansion": True}
    node_type, normalized = normalize_node_metadata(meta, "assumption")
    assert node_type == "parameter"
    assert normalized["kind"] == "assumption"
    assert normalized["input_id"] == "straight_pipe_section"
    assert normalized["required"] is True


def test_interaction_normalizes_to_parameter() -> None:
    meta = {"field": "pressure_loading", "mode": "decision"}
    node_type, normalized = normalize_node_metadata(meta, "interaction")
    assert node_type == "parameter"
    assert normalized["kind"] == "interaction"
    assert is_ui_parameter(normalized, node_type)


def test_lookup_normalizes_to_equation() -> None:
    meta = {"table_id": "asme_b31.3_A-1"}
    node_type, normalized = normalize_node_metadata(meta, "lookup")
    assert node_type == "equation"
    assert normalized["kind"] == "lookup"
    assert is_lookup_node(normalized, node_type)


def test_section_normalizes_to_text() -> None:
    meta = {"paragraph": "304.1.1"}
    node_type, normalized = normalize_node_metadata(meta, "standard_section")
    assert node_type == "text"
    assert normalized["kind"] == "section"
    assert is_section_node(normalized, node_type)


def test_unit_is_canonical() -> None:
    meta = {"symbol": "Pa", "dimension": "pressure"}
    node_type, normalized = normalize_node_metadata(meta, "unit")
    assert node_type == "unit"
    assert normalized["symbol"] == "Pa"


def test_quantity_is_canonical_and_runtime_fields_are_removed() -> None:
    meta = {
        "name": "Pressure",
        "dimension": "pressure",
        "value": 500,
        "runtime_unit": "psi",
    }
    node_type, normalized = normalize_node_metadata(meta, "quantity")
    assert node_type == "quantity"
    assert normalized["dimension"] == "pressure"
    assert "value" not in normalized
    assert "runtime_unit" not in normalized
    assert is_quantity_node(normalized, node_type)


def test_designation_is_canonical_and_not_a_quantity() -> None:
    meta = {
        "name": "Nominal Pipe Size",
        "symbol": "NPS",
        "description": "Pipe size designation.",
        "value": "4",
    }
    node_type, normalized = normalize_node_metadata(meta, "designation")
    assert node_type == "designation"
    assert normalized["symbol"] == "NPS"
    assert "value" not in normalized
    assert is_designation_node(normalized, node_type)
    assert not is_quantity_node(normalized, node_type)
