"""Tests for external equation graph edges."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.graph_store import GraphStore
from engine.reference.standards_paths import resolve_standard_pack
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_304_1_1_equation_edge(reader: StandardsReader) -> None:
    store = reader.graph_store
    store.load()
    outgoing = store.outgoing("304.1.1-a", edge_types={"references_equation", "equation"})
    assert len(outgoing) == 1
    assert outgoing[0].to_id == "asme-b313-304-1-1-eq-2"

    incoming = store.incoming("asme-b313-304-1-1-eq-2", edge_types={"references_equation", "equation", "authorized_by"})
    assert any(edge.from_id == "304.1.1-a" for edge in incoming)
