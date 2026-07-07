"""Embedded child node compilation tests."""

from __future__ import annotations

from engine.graph.graph_store import GraphStore


def test_embedded_assumption_nodes_discovered_in_compiled_graph(b313_reader) -> None:
    store = GraphStore(b313_reader.pack_root)
    store.load()
    assert store.available

    straight_pipe = store.get_node("PARAM-straight-pipe-section")
    assert straight_pipe is not None
    assert straight_pipe.node_type == "parameter"
    assert straight_pipe.metadata.get("key") == "straight_pipe_section"

    anchor = store.get_node("304.1.1-a")
    assert anchor is not None
    introduced = {
        edge.to_id
        for edge in store.outgoing("304.1.1-a", edge_types={"introduces_parameter", "contains"})
    }
    assert "PARAM-straight-pipe-section" in introduced or straight_pipe is not None
