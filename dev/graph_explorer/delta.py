"""Snapshot diffing for incremental WebSocket updates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dev.graph_explorer.serializer import GraphEdgeDto, GraphNodeDto, GraphSnapshotDto


@dataclass
class GraphDelta:
    revision: str
    added_nodes: list[dict[str, Any]] = field(default_factory=list)
    removed_nodes: list[str] = field(default_factory=list)
    changed_nodes: list[dict[str, Any]] = field(default_factory=list)
    added_edges: list[dict[str, Any]] = field(default_factory=list)
    removed_edges: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "delta",
            "revision": self.revision,
            "added_nodes": self.added_nodes,
            "removed_nodes": self.removed_nodes,
            "changed_nodes": self.changed_nodes,
            "added_edges": self.added_edges,
            "removed_edges": self.removed_edges,
        }


def compute_delta(previous: GraphSnapshotDto | None, current: GraphSnapshotDto) -> GraphDelta | None:
    if previous is None:
        return None
    if previous.revision == current.revision:
        return None

    prev_nodes = {node.id: node for node in previous.nodes}
    curr_nodes = {node.id: node for node in current.nodes}
    prev_edges = {edge.id: edge for edge in previous.edges}
    curr_edges = {edge.id: edge for edge in current.edges}

    added_nodes = [
        curr_nodes[node_id].to_dict()
        for node_id in sorted(curr_nodes.keys() - prev_nodes.keys())
    ]
    removed_nodes = sorted(prev_nodes.keys() - curr_nodes.keys())
    changed_nodes = [
        curr_nodes[node_id].to_dict()
        for node_id in sorted(curr_nodes.keys() & prev_nodes.keys())
        if _node_changed(prev_nodes[node_id], curr_nodes[node_id])
    ]

    added_edges = [
        curr_edges[edge_id].to_dict()
        for edge_id in sorted(curr_edges.keys() - prev_edges.keys())
    ]
    removed_edges = sorted(prev_edges.keys() - curr_edges.keys())

    return GraphDelta(
        revision=current.revision,
        added_nodes=added_nodes,
        removed_nodes=removed_nodes,
        changed_nodes=changed_nodes,
        added_edges=added_edges,
        removed_edges=removed_edges,
    )


def _node_changed(previous: GraphNodeDto, current: GraphNodeDto) -> bool:
    return (
        previous.node_type != current.node_type
        or previous.name != current.name
        or previous.description != current.description
        or previous.metadata != current.metadata
    )
