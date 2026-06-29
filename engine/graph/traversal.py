"""Graph traversal algorithms: BFS, DFS, topological sort."""

from __future__ import annotations

from collections import deque
from typing import Any, Callable

from engine.graph.conditions import GraphCycleError, when_clause_matches
from engine.graph.graph_store import GraphStore
from engine.reference.graph_db import GraphEdgeRecord
from models.graph import EdgeType, GraphEdge
from models.input import EngineeringInput


_TRAVERSAL_EDGE_TYPES = frozenset(
    {
        EdgeType.REQUIRES.value,
        EdgeType.NEXT_STEP.value,
        EdgeType.DEPENDENCY.value,
        EdgeType.CONTAINS.value,
        EdgeType.ANCHORS_TO.value,
        EdgeType.DEFINES.value,
        EdgeType.CALCULATES.value,
        "requires",
        "next_step",
        "dependency",
        "contains",
        "anchors_to",
    }
)


def _edge_active(
    edge: GraphEdgeRecord,
    inputs: dict[str, EngineeringInput],
) -> bool:
    when = edge.metadata.get("when") if edge.metadata else None
    if when and isinstance(when, dict):
        return when_clause_matches(when, inputs)
    return True


def bfs_neighbors(
    store: GraphStore,
    start_id: str,
    *,
    depth: int = 1,
    edge_types: set[str] | None = None,
    direction: str = "outgoing",
) -> dict[int, list[str]]:
    """Return nodes grouped by BFS depth from start_id."""
    if depth < 0:
        return {}
    levels: dict[int, list[str]] = {0: [start_id]}
    visited: set[str] = {start_id}
    for current_depth in range(depth):
        next_level: list[str] = []
        for node_id in levels.get(current_depth, []):
            edges = (
                store.outgoing(node_id, edge_types=edge_types)
                if direction == "outgoing"
                else store.incoming(node_id, edge_types=edge_types)
            )
            for edge in edges:
                neighbor = edge.to_id if direction == "outgoing" else edge.from_id
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                next_level.append(neighbor)
        if next_level:
            levels[current_depth + 1] = next_level
    return levels


def dfs_collect(
    store: GraphStore,
    start_id: str,
    *,
    inputs: dict[str, EngineeringInput],
    edge_types: set[str] | None = None,
    visit: Callable[[str], bool] | None = None,
) -> tuple[list[str], list[GraphEdgeRecord]]:
    """Depth-first collect reachable nodes and active edges."""
    if edge_types is None:
        edge_types = set(_TRAVERSAL_EDGE_TYPES)
    order: list[str] = []
    edges: list[GraphEdgeRecord] = []
    visited: set[str] = set()

    def walk(node_id: str, visiting: set[str]) -> None:
        if node_id in visiting:
            raise GraphCycleError(f"Dependency cycle detected at node: {node_id}")
        if node_id in visited:
            return
        if visit and not visit(node_id):
            return
        visiting.add(node_id)
        visited.add(node_id)
        order.append(node_id)
        for edge in store.outgoing(node_id, edge_types=edge_types):
            if not _edge_active(edge, inputs):
                continue
            edges.append(edge)
            walk(edge.to_id, visiting.copy())

    walk(start_id, set())
    return order, edges


def topological_order(
    nodes: set[str],
    edges: list[GraphEdgeRecord] | list[GraphEdge],
    *,
    priority_key: Callable[[str], tuple[Any, ...]] | None = None,
) -> tuple[str, ...]:
    """Return nodes in dependency order (dependencies first)."""
    in_degree: dict[str, int] = {node: 0 for node in nodes}
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}

    for edge in edges:
        from_id = edge.from_id if hasattr(edge, "from_id") else edge.from_node  # type: ignore[union-attr]
        to_id = edge.to_id if hasattr(edge, "to_id") else edge.to_node  # type: ignore[union-attr]
        if from_id not in nodes or to_id not in nodes:
            continue
        adjacency[from_id].append(to_id)
        in_degree[to_id] = in_degree.get(to_id, 0) + 1

    queue: deque[str] = deque(
        sorted(
            (node for node, degree in in_degree.items() if degree == 0),
            key=priority_key or (lambda item: item),
        )
    )
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        dependents = sorted(
            adjacency.get(node, []),
            key=priority_key or (lambda item: item),
        )
        for dependent in dependents:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(order) != len(nodes):
        raise GraphCycleError("Dependency cycle detected during topological sort")

    return tuple(order)
