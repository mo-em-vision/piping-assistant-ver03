"""Graph Engine — dependency resolution and execution plan generation."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

from engine.reference.standards_reader import StandardsReader
from models.execution import ExecutionPlan
from models.graph import EdgeType, GraphEdge, GraphVersion
from models.input import EngineeringInput
from models.planning import WorkflowCandidate


# Future workflow stubs surfaced when keywords match (not yet implemented).
_STUB_ROOTS: tuple[dict[str, str | float | bool], ...] = (
    {
        "slug": "integrity_check",
        "title": "Pipe Integrity Verification",
        "engineering_intent": "pipe_integrity_verification",
        "keywords": ("integrity", "verification", "inspect"),
        "confidence": 0.55,
        "implemented": False,
    },
    {
        "slug": "pressure_test_verification",
        "title": "Pressure Test Verification",
        "engineering_intent": "pressure_test_verification",
        "keywords": ("pressure test", "hydrotest", "pneumatic"),
        "confidence": 0.5,
        "implemented": False,
    },
)


def normalize_root_id(root_ref: str) -> str:
    """Convert root path references to standards slug ids."""
    text = root_ref.strip().strip("/")
    if text.endswith("root.md"):
        text = text[: -len("root.md")].strip("/")
    if text.startswith("roots/"):
        text = text[len("roots/") :].strip("/")
    return text.split("/")[0] if text else root_ref


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

    def discover_roots(
        self,
        reader: StandardsReader,
        *,
        workflow: str | None = None,
        keywords: list[str] | None = None,
    ) -> list[WorkflowCandidate]:
        """Scan standards roots and return workflow candidates ranked by match confidence."""
        candidates: list[WorkflowCandidate] = []
        keyword_text = " ".join(keywords or []).lower()

        for path in sorted(reader.roots_dir.glob("*/root.md")):
            record = reader.load_file(path)
            slug = path.parent.name
            intent = str(record.metadata.get("engineering_intent", "") or "")
            title = str(record.metadata.get("title", slug))
            confidence = 0.4

            if workflow and (workflow == intent or workflow == slug):
                confidence = 0.95
            elif workflow and workflow.replace("-", "_") in slug.replace("-", "_"):
                confidence = 0.9
            else:
                for token in (intent, title, slug, str(record.metadata.get("purpose", ""))):
                    if token and token.lower() in keyword_text:
                        confidence = max(confidence, 0.75)

            if confidence >= 0.4:
                candidates.append(
                    WorkflowCandidate(
                        root_id=slug,
                        title=title,
                        engineering_intent=intent or None,
                        standard="ASME B31.3",
                        confidence=confidence,
                        implemented=True,
                    )
                )

        for stub in _STUB_ROOTS:
            stub_keywords = tuple(str(k).lower() for k in stub["keywords"])  # type: ignore[index]
            if workflow and workflow == str(stub["engineering_intent"]):
                match = True
            elif keyword_text:
                match = any(kw in keyword_text for kw in stub_keywords)
            else:
                match = False

            if match:
                candidates.append(
                    WorkflowCandidate(
                        root_id=str(stub["slug"]),
                        title=str(stub["title"]),
                        engineering_intent=str(stub["engineering_intent"]),
                        standard="ASME B31.3",
                        confidence=float(stub["confidence"]),  # type: ignore[arg-type]
                        implemented=bool(stub["implemented"]),
                    )
                )

        candidates.sort(key=lambda item: item.confidence, reverse=True)
        return candidates

    def required_user_inputs(
        self,
        root_id: str,
        reader: StandardsReader,
        *,
        existing_inputs: set[str] | None = None,
    ) -> list[str]:
        """Collect required user-provided inputs for a workflow root (no execution)."""
        slug = normalize_root_id(root_id)
        plan = self.build_plan(task_id="preview", root_id=slug, inputs={}, reader=reader)
        existing = existing_inputs or set()
        required: list[str] = []
        seen: set[str] = set()

        for node_id in plan.execution_order:
            record = reader.load(node_id)
            if str(record.metadata.get("type", "")) == "root":
                continue
            for spec in record.metadata.get("inputs", []) or []:
                if not isinstance(spec, dict):
                    continue
                input_id = str(spec.get("id", ""))
                if not input_id or input_id in seen or input_id in existing:
                    continue
                if not bool(spec.get("required", True)):
                    continue
                source = str(spec.get("source", "user_input"))
                if source in ("user_input", "table") or (
                    source == "default" and spec.get("default") is None
                ):
                    seen.add(input_id)
                    required.append(input_id)

        return required

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
