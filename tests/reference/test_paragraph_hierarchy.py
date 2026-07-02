"""Paragraph hierarchy helper tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.paragraph_hierarchy import (
    hierarchy_entries,
    paragraph_reference,
    resolve_hierarchy_chain,
    section_label,
)
from engine.reference.standards_reader import StandardsReader


@pytest.fixture
def reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_paragraph_reference_falls_back_to_node_id() -> None:
    metadata = {"id": "304.1.1", "type": "paragraph"}
    assert paragraph_reference(metadata) == "304.1.1"


def test_section_label_reads_hierarchy_root_title() -> None:
    metadata = {
        "id": "304.1.1",
        "hierarchy_chain": [
            {"node_id": "304.1"},
            {"node_id": "304", "title": "304 Pressure Design of Components"},
        ],
    }
    assert section_label(metadata) == "304 Pressure Design of Components"
    assert hierarchy_entries(metadata) == []


def test_section_label_prefers_legacy_section_field() -> None:
    metadata = {
        "id": "304.1.2",
        "section": "304 Pressure Design of Components",
        "hierarchy": [{"node_id": "304.1"}],
    }
    assert section_label(metadata) == "304 Pressure Design of Components"


def test_resolve_hierarchy_chain_for_304_1_1(reader: StandardsReader) -> None:
    chain = resolve_hierarchy_chain(reader, "304.1.1")
    assert [item["node_id"] for item in chain] == ["304.1", "304"]
    assert chain[-1].get("title") == "304 Pressure Design of Components"


def test_resolve_hierarchy_chain_for_304_1(reader: StandardsReader) -> None:
    chain = resolve_hierarchy_chain(reader, "304.1")
    assert chain == [{"node_id": "304", "title": "304 Pressure Design of Components"}]


def test_resolve_hierarchy_chain_for_304_root(reader: StandardsReader) -> None:
    assert resolve_hierarchy_chain(reader, "304") == []


def test_resolve_hierarchy_chain_for_304_3_1(reader: StandardsReader) -> None:
    chain = resolve_hierarchy_chain(reader, "304.3.1")
    assert [item["node_id"] for item in chain] == ["304.3", "304"]


def test_eq_2_equation_loads_by_node_id(reader: StandardsReader) -> None:
    record = reader.load("304.1.1-eq-2")
    assert record.metadata.get("executor") == "calculate_minimum_required_thickness"
    assert "t_m = t + c" in str(record.metadata.get("display", ""))


def test_eq_2_is_standalone_equation_node(reader: StandardsReader) -> None:
    record = reader.load("304.1.1-eq-2")
    assert record.node_id == "asme_b313_304_1_1_eq_2"
    assert record.metadata.get("type") == "equation"
    assert record.metadata.get("key") == "asme_b313_304_1_1_eq_2"
    assert record.metadata.get("parent_node_id") is None or record.metadata.get("edges")


def test_304_1_1_references_external_eq_2_graph_edge(reader: StandardsReader) -> None:
    store = reader.graph_store
    store.load()

    node_meta = store.metadata("304.1.1")
    assert node_meta.get("type") == "paragraph"
    assert node_meta.get("edges")

    outgoing = store.outgoing("304.1.1", edge_types={"references_equation", "equation"})
    assert len(outgoing) == 1
    assert outgoing[0].to_id == "asme_b313_304_1_1_eq_2"
    assert (outgoing[0].metadata or {}).get("subsection") == "a"

    incoming = store.incoming("asme_b313_304_1_1_eq_2", edge_types={"references_equation", "equation"})
    assert len(incoming) == 1
    assert incoming[0].from_id == "304.1.1"
    assert store.get_node("asme_b313_304_1_1_eq_2") is not None
