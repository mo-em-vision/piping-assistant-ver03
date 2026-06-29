"""Canonical node type normalization tests."""

from __future__ import annotations

from engine.reference.node_types import (
    is_lookup_node,
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
