"""In-memory graph store backed by compiled sources (SQLite is an optional cache)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.graph.pack_graph import PackGraph
from engine.reference.graph_cache import build_or_load_graph
from engine.reference.graph_db import GraphEdgeRecord, GraphNodeRecord
from engine.reference.graph_edge_schema import REVERSE_EDGE_TYPE, expand_incoming_edge_types
from engine.reference.pack_graph_db import resolve_pack_graph_db


def _matches_incoming_type(edge: GraphEdgeRecord, edge_types: set[str]) -> bool:
    stored_type = edge.edge_type
    if stored_type in edge_types:
        return True
    reverse_type = REVERSE_EDGE_TYPE.get(stored_type)
    return bool(reverse_type and reverse_type in edge_types)


@dataclass
class GraphStore:
    """Load micro-graph nodes and edges with adjacency indexes."""

    pack_root: Path
    _graph: PackGraph | None = field(default=None, repr=False)
    _nodes: dict[str, GraphNodeRecord] = field(default_factory=dict, repr=False)
    _aliases: dict[str, str] = field(default_factory=dict, repr=False)
    _outgoing: dict[str, list[GraphEdgeRecord]] = field(default_factory=dict, repr=False)
    _incoming: dict[str, list[GraphEdgeRecord]] = field(default_factory=dict, repr=False)
    _loaded: bool = field(default=False, repr=False)

    @property
    def db_path(self) -> Path:
        return resolve_pack_graph_db(self.pack_root)

    @property
    def graph(self) -> PackGraph | None:
        self.load()
        return self._graph

    @property
    def available(self) -> bool:
        self.load()
        return bool(self._nodes)

    def load(self, *, prefer_cache: bool = True) -> None:
        if self._loaded:
            return
        graph = build_or_load_graph(self.pack_root, prefer_cache=prefer_cache)
        self._graph = graph
        self._nodes = dict(graph.nodes)
        self._aliases = dict(graph.aliases)
        self._outgoing.clear()
        self._incoming.clear()
        for edge in graph.edges:
            self._outgoing.setdefault(edge.from_id, []).append(edge)
            self._incoming.setdefault(edge.to_id, []).append(edge)
        self._loaded = True

    def reload(self, *, prefer_cache: bool = True) -> None:
        """Drop indexes and rebuild from sources (or a fresh cache)."""
        self._loaded = False
        self._graph = None
        self.load(prefer_cache=prefer_cache)

    def resolve_node_id(self, reference: str) -> str | None:
        self.load()
        wanted = reference.strip()
        if not wanted:
            return None
        if wanted in self._nodes:
            return wanted
        return self._aliases.get(wanted)

    def get_node(self, node_id: str) -> GraphNodeRecord | None:
        self.load()
        resolved = self.resolve_node_id(node_id)
        if resolved is None:
            return None
        return self._nodes.get(resolved)

    def list_nodes(self, *, node_type: str | None = None) -> list[GraphNodeRecord]:
        self.load()
        nodes = list(self._nodes.values())
        if node_type:
            nodes = [node for node in nodes if node.node_type == node_type]
        return sorted(nodes, key=lambda item: item.node_id)

    def list_workflows(self) -> list[GraphNodeRecord]:
        return self.list_nodes(node_type="workflow")

    def outgoing(
        self,
        node_id: str,
        *,
        edge_types: set[str] | None = None,
    ) -> list[GraphEdgeRecord]:
        self.load()
        resolved = self.resolve_node_id(node_id)
        if resolved is None:
            return []
        edges = list(self._outgoing.get(resolved, []))
        if edge_types:
            expanded = expand_incoming_edge_types(edge_types) or edge_types
            edges = [edge for edge in edges if edge.edge_type in expanded]
        return edges

    def incoming(
        self,
        node_id: str,
        *,
        edge_types: set[str] | None = None,
    ) -> list[GraphEdgeRecord]:
        self.load()
        resolved = self.resolve_node_id(node_id)
        if resolved is None:
            return []
        edges = list(self._incoming.get(resolved, []))
        if edge_types:
            edges = [edge for edge in edges if _matches_incoming_type(edge, edge_types)]
        return edges

    def metadata(self, node_id: str) -> dict[str, Any]:
        node = self.get_node(node_id)
        return dict(node.metadata) if node else {}

    def node_type(self, node_id: str) -> str | None:
        node = self.get_node(node_id)
        return node.node_type if node else None

    def body(self, node_id: str) -> str:
        node = self.get_node(node_id)
        return node.body if node else ""
