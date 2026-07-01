"""Graph edge schema and reverse index tests."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_store import GraphStore
from engine.reference.standards_reader import StandardsReader


def test_incoming_referenced_by_matches_outgoing_references() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    store = reader.graph_store
    store.load()
    outgoing = store.outgoing("304.1.1", edge_types={"references"})
    incoming = store.incoming("304.1.2", edge_types={"referenced_by"})
    assert any(edge.to_id == "304.1.2" for edge in outgoing)
    assert any(edge.from_id == "304.1.1" for edge in incoming)
