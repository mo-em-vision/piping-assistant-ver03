"""JSON-serializable DTOs for the graph explorer API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GraphEdgeDto:
    id: str
    source: str
    target: str
    edge_type: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphNodeDto:
    id: str
    node_type: str
    name: str
    description: str
    pack: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphContextDto:
    task_id: str | None
    workflow_id: str | None
    session_id: str
    node_count: int
    edge_count: int
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphSnapshotDto:
    revision: str
    context: GraphContextDto
    nodes: list[GraphNodeDto]
    edges: list[GraphEdgeDto]

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "context": self.context.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


@dataclass
class EdgeRefDto:
    edge_type: str
    peer_id: str
    direction: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NodeDetailDto:
    id: str
    node_type: str
    name: str
    description: str
    inputs: list[str]
    outputs: list[str]
    incoming_edges: list[EdgeRefDto]
    outgoing_edges: list[EdgeRefDto]
    metadata: dict[str, Any]
    standard_refs: list[str]
    body_preview: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "incoming_edges": [edge.to_dict() for edge in self.incoming_edges],
            "outgoing_edges": [edge.to_dict() for edge in self.outgoing_edges],
            "metadata": self.metadata,
            "standard_refs": self.standard_refs,
            "body_preview": self.body_preview,
        }
