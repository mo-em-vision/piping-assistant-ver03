"""Graph edge schema and reverse index tests."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_store import GraphStore
from engine.reference.graph_edge_schema import workflow_anchor_target
from engine.reference.standards_reader import StandardsReader


def test_incoming_referenced_by_matches_outgoing_references() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    store = reader.graph_store
    store.load()
    outgoing = store.outgoing("304.1.1-a", edge_types={"references_equation", "related_to"})
    incoming = store.incoming("asme-b313-304-1-1-eq-2", edge_types={"referenced_by", "references_equation"})
    assert any(edge.to_id == "asme-b313-304-1-1-eq-2" for edge in outgoing)
    assert any(edge.from_id == "304.1.1-a" for edge in incoming)


def test_workflow_anchor_target_from_entry_points() -> None:
    metadata = {
        "entry_points": [
            {"paragraph": "304.1.1-a", "role": "definition_anchor"},
        ],
    }
    assert workflow_anchor_target(metadata) == "304.1.1-a"


def test_workflow_anchor_target_from_parameter_entry_points() -> None:
    metadata = {
        "entry_points": [
            {
                "parameter": "PARAM-maximum-allowable-working-pressure",
                "role": "definition_anchor",
            },
        ],
    }
    assert workflow_anchor_target(metadata) == "PARAM-maximum-allowable-working-pressure"


def test_workflow_anchor_target_prefers_starts_from_paragraph_edge() -> None:
    metadata = {
        "entry_points": [
            {"paragraph": "304.1.1-a", "role": "definition_anchor"},
        ],
        "edges": [
            {"type": "starts_from_paragraph", "target": "304.1.2-a"},
        ],
    }
    assert workflow_anchor_target(metadata) == "304.1.2-a"


def test_mawp_workflow_anchor_from_live_graph() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    store = reader.graph_store
    store.load()
    wf = store.get_node("WF-MAWP")
    assert wf is not None
    assert workflow_anchor_target(wf.metadata) == "PARAM-maximum-allowable-working-pressure"


def test_pipe_wall_workflow_anchor_from_live_graph() -> None:
    root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
    store = reader.graph_store
    store.load()
    wf = store.get_node("WF-PIPE-WALL-THICKNESS")
    assert wf is not None
    assert workflow_anchor_target(wf.metadata) == "304.1.1-a"
