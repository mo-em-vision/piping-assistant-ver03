"""Tests for relationship taxonomy normalization and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.graph_store import GraphStore
from engine.graph.relationship_resolver import node_requires_items
from engine.reference.graph_compile import compile_metadata_edges, validate_edge_item
from engine.reference.relationship_taxonomy import (
    KNOWLEDGE_EDGE_TYPES,
    LEGACY_TRANSPORT_TYPES,
    normalize_authoring_edge,
)
from engine.reference.standards_reader import StandardsReader


@pytest.mark.parametrize(
    ("legacy", "source_type", "expected_type"),
    [
        (
            {"type": "references", "target": "AUTH-ASME-B31.3", "role": "belongs_to_authority"},
            "paragraph",
            "belongs_to_authority",
        ),
        (
            {"type": "references", "target": "304.1.2", "role": "authorized_by"},
            "equation",
            "authorized_by",
        ),
        ({"type": "requires", "target": "param-P", "alias": "P"}, "equation", "requires_parameter"),
        (
            {"type": "parameter", "target": "param-t", "role": "calculates"},
            "equation",
            "calculates_parameter",
        ),
        (
            {"type": "equation", "target": "asme_b313_304_1_2_wall_thickness"},
            "paragraph",
            "references_equation",
        ),
        (
            {"type": "references", "target": "304.1.1", "role": "starts_from_paragraph"},
            "workflow",
            "starts_from_paragraph",
        ),
        ({"type": "contains", "target": "304.1.1", "role": "paragraph"}, "authority", "contains_paragraph"),
    ],
)
def test_normalize_legacy_edges(legacy: dict, source_type: str, expected_type: str) -> None:
    normalized = normalize_authoring_edge(legacy, source_node_type=source_type, allow_legacy=True)
    assert normalized is not None
    assert normalized["type"] == expected_type


def test_validate_rejects_bare_references_without_role() -> None:
    issues = validate_edge_item(
        {"type": "references", "target": "304.1.1"},
        source_node_type="paragraph",
        allow_legacy=False,
    )
    assert any("legacy transport" in issue or "generic references" in issue for issue in issues)


def test_compile_stores_taxonomy_edge_types() -> None:
    edges = compile_metadata_edges(
        "asme_b313_304_1_2_wall_thickness",
        {
            "type": "equation",
            "edges": [
                {"type": "authorized_by", "target": "304.1.2"},
                {"type": "requires_parameter", "target": "param-P", "alias": "P"},
            ],
        },
    )
    types = {edge[2] for edge in edges}
    assert "authorized_by" in types
    assert "requires_parameter" in types


def test_migrated_equation_requires_bindings() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    store = GraphStore(reader.pack_root)
    store.load()
    items = node_requires_items(store, "asme_b313_304_1_2_wall_thickness")
    assert items
    aliases = {item.get("alias") for item in items}
    assert "P" in aliases


def test_knowledge_yaml_avoids_legacy_transport_types() -> None:
    root = Path(__file__).resolve().parents[2]
    knowledge = root / "knowledge"
    offenders: list[str] = []
    for path in knowledge.rglob("*.yaml"):
        if path.name in {"execution.yaml", "runtime.yaml", "nomenclature.yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        import yaml

        end = text.split("---", 2)[1]
        meta = yaml.safe_load(end) or {}
        for item in meta.get("edges") or []:
            if not isinstance(item, dict):
                continue
            edge_type = str(item.get("type") or "")
            if edge_type in LEGACY_TRANSPORT_TYPES and edge_type in {"references", "requires", "parameter", "equation", "table", "contains", "constrains"}:
                offenders.append(f"{path.relative_to(root)}: {edge_type}")
    assert offenders == [], f"legacy transport edges remain: {offenders}"


def test_taxonomy_vocabulary_includes_core_types() -> None:
    for edge_type in (
        "belongs_to_authority",
        "authorized_by",
        "requires_parameter",
        "calculates_parameter",
        "starts_from_paragraph",
        "references_equation",
    ):
        assert edge_type in KNOWLEDGE_EDGE_TYPES
