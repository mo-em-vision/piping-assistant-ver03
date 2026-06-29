"""Graph analysis utilities for the developer explorer."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from dev.graph_explorer.serializer import GraphEdgeDto, GraphNodeDto


@dataclass
class GraphAnalysisReport:
    orphan_nodes: list[str] = field(default_factory=list)
    no_incoming: list[str] = field(default_factory=list)
    no_outgoing: list[str] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    duplicate_names: dict[str, list[str]] = field(default_factory=dict)
    disconnected_components: list[list[str]] = field(default_factory=list)
    highly_connected: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_graph(
    nodes: list[GraphNodeDto],
    edges: list[GraphEdgeDto],
    *,
    hub_threshold: int = 5,
) -> GraphAnalysisReport:
    node_ids = {node.id for node in nodes}
    in_degree: dict[str, int] = {node_id: 0 for node_id in node_ids}
    out_degree: dict[str, int] = {node_id: 0 for node_id in node_ids}
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    directed_out: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            continue
        out_degree[edge.source] = out_degree.get(edge.source, 0) + 1
        in_degree[edge.target] = in_degree.get(edge.target, 0) + 1
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)
        directed_out[edge.source].append(edge.target)

    orphans = [
        node_id
        for node_id in node_ids
        if in_degree.get(node_id, 0) == 0 and out_degree.get(node_id, 0) == 0
    ]
    no_incoming = [node_id for node_id in node_ids if in_degree.get(node_id, 0) == 0 and node_id not in orphans]
    no_outgoing = [node_id for node_id in node_ids if out_degree.get(node_id, 0) == 0 and node_id not in orphans]

    cycles = _find_cycles(node_ids, directed_out)
    duplicate_names = _find_duplicate_names(nodes)
    components = _connected_components(node_ids, adjacency)
    highly_connected = [
        {
            "node_id": node_id,
            "in_degree": in_degree.get(node_id, 0),
            "out_degree": out_degree.get(node_id, 0),
            "total_degree": in_degree.get(node_id, 0) + out_degree.get(node_id, 0),
        }
        for node_id in node_ids
        if in_degree.get(node_id, 0) + out_degree.get(node_id, 0) >= hub_threshold
    ]
    highly_connected.sort(key=lambda item: item["total_degree"], reverse=True)

    return GraphAnalysisReport(
        orphan_nodes=sorted(orphans),
        no_incoming=sorted(no_incoming),
        no_outgoing=sorted(no_outgoing),
        cycles=cycles,
        duplicate_names=duplicate_names,
        disconnected_components=components,
        highly_connected=highly_connected,
    )


def _find_duplicate_names(nodes: list[GraphNodeDto]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        key = node.name.strip().lower()
        if key:
            buckets[key].append(node.id)
    return {name: ids for name, ids in sorted(buckets.items()) if len(ids) > 1}


def _connected_components(node_ids: set[str], adjacency: dict[str, set[str]]) -> list[list[str]]:
    remaining = set(node_ids)
    components: list[list[str]] = []
    while remaining:
        start = min(remaining)
        stack = [start]
        component: list[str] = []
        remaining.remove(start)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in adjacency.get(current, ()):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return components


def _find_cycles(node_ids: set[str], directed_out: dict[str, list[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    visited: set[str] = set()
    stack: list[str] = []
    on_stack: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in on_stack:
            idx = stack.index(node_id)
            cycle = stack[idx:] + [node_id]
            if len(cycle) > 2:
                cycles.append(cycle)
            return
        if node_id in visited:
            return
        visited.add(node_id)
        on_stack.add(node_id)
        stack.append(node_id)
        for neighbor in directed_out.get(node_id, []):
            if neighbor in node_ids:
                visit(neighbor)
        stack.pop()
        on_stack.remove(node_id)

    for node_id in sorted(node_ids):
        visit(node_id)

    unique: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for cycle in cycles:
        normalized = tuple(sorted(set(cycle)))
        if normalized not in seen:
            seen.add(normalized)
            unique.append(cycle)
    return unique
