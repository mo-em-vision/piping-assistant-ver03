"""Tests for lookup and validation_rule relationship taxonomy rules."""

from __future__ import annotations

from engine.reference.relationship_taxonomy import (
    KNOWLEDGE_EDGE_TYPES,
    RELATIONSHIP_RULES,
    RUNTIME_ONLY_EDGE_TYPES,
    normalize_authoring_edge,
    validate_taxonomy_edge,
)


def test_lookup_and_valrule_edge_types_are_knowledge_types() -> None:
    for edge_type in (
        "reads_table",
        "returns_parameter",
        "references_lookup",
        "references_validation_rule",
        "constrains_equation",
        "creates_warning",
        "may_use_lookup",
        "may_use_validation_rule",
    ):
        assert edge_type in KNOWLEDGE_EDGE_TYPES


def test_runtime_validation_edges_are_runtime_only() -> None:
    assert "produces_validation_result" in RUNTIME_ONLY_EDGE_TYPES
    assert "blocks_goal" in RUNTIME_ONLY_EDGE_TYPES


def test_validates_parameter_not_allowed_from_equation() -> None:
    rule = RELATIONSHIP_RULES["validates_parameter"]
    assert rule.source_types is not None
    assert "equation" not in rule.source_types
    assert "validation_rule" in rule.source_types


def test_calculates_parameter_equation_only() -> None:
    rule = RELATIONSHIP_RULES["calculates_parameter"]
    assert rule.source_types == frozenset({"equation", "calculation"})


def test_requires_lookup_normalizes_to_references_lookup() -> None:
    normalized = normalize_authoring_edge(
        {"type": "requires_lookup", "target": "LOOKUP-B313-material-allowable-stress"},
        source_node_type="paragraph",
        allow_legacy=True,
    )
    assert normalized is not None
    assert normalized["type"] == "references_lookup"


def test_used_by_lookup_rejected_for_authoring() -> None:
    normalized = normalize_authoring_edge(
        {"type": "used_by_lookup", "target": "LOOKUP-B313-material-allowable-stress"},
        source_node_type="table",
        allow_legacy=True,
    )
    assert normalized is None


def test_lookup_reads_table_edge_validates() -> None:
    issues = validate_taxonomy_edge(
        {"type": "reads_table", "target": "TABLE-B313-allowable-stress"},
        source_node_type="lookup",
    )
    assert issues == []
