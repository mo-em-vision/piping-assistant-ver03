"""Tests for graph analysis utilities."""

from __future__ import annotations

from dev.graph_explorer.analysis import analyze_graph
from dev.graph_explorer.serializer import GraphEdgeDto, GraphNodeDto


def _node(node_id: str, name: str = "") -> GraphNodeDto:
    return GraphNodeDto(
        id=node_id,
        node_type="parameter",
        name=name or node_id,
        description="",
        pack="test",
        metadata={},
    )


def test_orphan_detection() -> None:
    nodes = [_node("a"), _node("b"), _node("c")]
    edges = [GraphEdgeDto(id="a|requires|b", source="a", target="b", edge_type="requires")]
    report = analyze_graph(nodes, edges)
    assert report.orphan_nodes == ["c"]
    assert "c" not in report.no_incoming


def test_duplicate_names() -> None:
    nodes = [_node("a", "Pressure"), _node("b", "pressure"), _node("c", "Unique")]
    report = analyze_graph(nodes, [])
    assert "pressure" in report.duplicate_names
    assert set(report.duplicate_names["pressure"]) == {"a", "b"}


def test_cycle_detection() -> None:
    nodes = [_node("a"), _node("b"), _node("c")]
    edges = [
        GraphEdgeDto(id="a|requires|b", source="a", target="b", edge_type="requires"),
        GraphEdgeDto(id="b|requires|c", source="b", target="c", edge_type="requires"),
        GraphEdgeDto(id="c|requires|a", source="c", target="a", edge_type="requires"),
    ]
    report = analyze_graph(nodes, edges)
    assert report.cycles


def test_highly_connected_hub() -> None:
    nodes = [_node("hub"), _node("n1"), _node("n2"), _node("n3")]
    edges = [
        GraphEdgeDto(id="hub|requires|n1", source="hub", target="n1", edge_type="requires"),
        GraphEdgeDto(id="hub|requires|n2", source="hub", target="n2", edge_type="requires"),
        GraphEdgeDto(id="hub|requires|n3", source="hub", target="n3", edge_type="requires"),
        GraphEdgeDto(id="n1|requires|hub", source="n1", target="hub", edge_type="requires"),
        GraphEdgeDto(id="n2|requires|hub", source="n2", target="hub", edge_type="requires"),
    ]
    report = analyze_graph(nodes, edges, hub_threshold=4)
    assert any(item["node_id"] == "hub" for item in report.highly_connected)
