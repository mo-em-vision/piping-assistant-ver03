"""In-memory micro-graph for one standards pack (source of truth at runtime)."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.reference.graph_db import GraphEdgeRecord, GraphNodeRecord


@dataclass
class PackGraph:
    """Compiled nodes, semantic edges, and id aliases for a standards pack."""

    pack_root: str
    source_fingerprint: str
    nodes: dict[str, GraphNodeRecord] = field(default_factory=dict)
    edges: list[GraphEdgeRecord] = field(default_factory=list)
    aliases: dict[str, str] = field(default_factory=dict)

    def resolve_node_id(self, reference: str) -> str | None:
        wanted = reference.strip()
        if not wanted:
            return None
        if wanted in self.nodes:
            return wanted
        return self.aliases.get(wanted)

    def get_node(self, node_id: str) -> GraphNodeRecord | None:
        resolved = self.resolve_node_id(node_id)
        if resolved is None:
            return None
        return self.nodes.get(resolved)

    @property
    def node_ids(self) -> set[str]:
        return set(self.nodes.keys())
