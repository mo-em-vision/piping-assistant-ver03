"""Graph Engine — dependency resolution and execution plan generation."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

from engine.reference.standards_reader import StandardsReader
from models.execution import ExecutionPlan
from models.graph import EdgeType, GraphEdge, GraphVersion
from models.input import EngineeringInput


class GraphCycleError(ValueError):
    """Raised when a dependency cycle is detected."""


class GraphEngine:
    """Build deterministic execution plans from standards node dependencies."""

    def build_plan(
        self,
        *,
        task_id: str,
        root_id: str,
        inputs: dict[str, EngineeringInput],
        reader: StandardsReader,
    ) -> ExecutionPlan:
        root_record = reader.load(root_id)
        nodes_set: set[str] = set()
        edges: list[GraphEdge] = []
        node_versions: dict[str, str] = {}

        self._collect_nodes(root_id, reader, nodes_set, edges, node_versions, visiting=set())

        execution_order = self._topological_sort(nodes_set, edges)
        graph_version = GraphVersion(
            graph_id=root_record.node_id,
            created=datetime.now(timezone.utc),
            standard_versions={"asme_b31.3": str(root_record.metadata.get("version", "1.0"))},
            nodes=tuple(sorted(nodes_set)),
            edges=tuple(edges),
        )

        return ExecutionPlan(
            task_id=task_id,
            root=root_record.node_id,
            nodes=tuple(sorted(nodes_set)),
            execution_order=execution_order,
            inputs=dict(inputs),
            dependencies=tuple(edges),
            graph_version=graph_version,
        )

    def _collect_nodes(
        self,
        node_id: str,
        reader: StandardsReader,
        nodes: set[str],
        edges: list[GraphEdge],
        node_versions: dict[str, str],
        *,
        visiting: set[str],
    ) -> None:
        if node_id in visiting:
            raise GraphCycleError(f"Dependency cycle detected at node: {node_id}")

        record = reader.load(node_id)
        nodes.add(record.node_id)
        node_versions[record.node_id] = str(record.metadata.get("version", "1.0"))
        visiting.add(record.node_id)

        for dep_id in record.depends_on:
            dep_type = EdgeType.DEPENDENCY
            for item in record.metadata.get("depends_on", []) or []:
                if isinstance(item, dict) and item.get("node_id") == dep_id:
                    raw_type = str(item.get("dependency_type", "dependency"))
                    try:
                        dep_type = EdgeType(raw_type)
                    except ValueError:
                        dep_type = EdgeType.DEPENDENCY
                    break

            edges.append(
                GraphEdge(
                    from_node=dep_id,
                    to_node=record.node_id,
                    type=dep_type,
                    reason=f"{record.node_id} depends on {dep_id}",
                )
            )
            self._collect_nodes(
                dep_id,
                reader,
                nodes,
                edges,
                node_versions,
                visiting=visiting.copy(),
            )

    @staticmethod
    def _topological_sort(nodes: set[str], edges: list[GraphEdge]) -> tuple[str, ...]:
        """Return nodes in dependency order (dependencies first)."""
        in_degree: dict[str, int] = {node: 0 for node in nodes}
        adjacency: dict[str, list[str]] = {node: [] for node in nodes}

        for edge in edges:
            if edge.from_node not in nodes or edge.to_node not in nodes:
                continue
            adjacency[edge.from_node].append(edge.to_node)
            in_degree[edge.to_node] = in_degree.get(edge.to_node, 0) + 1

        queue: deque[str] = deque(node for node, degree in in_degree.items() if degree == 0)
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for dependent in adjacency.get(node, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(nodes):
            raise GraphCycleError("Dependency cycle detected during topological sort")

        return tuple(order)
