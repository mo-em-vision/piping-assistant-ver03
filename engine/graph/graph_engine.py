"""Graph Engine — dependency resolution and execution plan generation."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

from engine.graph.assumption_checker import (
    AssumptionEvaluation,
    evaluate_path_expansion_assumptions,
    field_value,
    normalize_assumption_value,
    question_for,
    NodeAssumptionSpec,
)
from engine.graph.node_interaction import (
    collect_path_interactions,
    collect_root_interactions,
    evaluate_pending_interactions,
    find_interaction,
    node_expansion_ready,
    propose_decision_defaults,
    propose_default_values,
    question_for_interaction,
)
from engine.graph.parameter_registry import seed_parameter_registry
from engine.reference.nomenclature_resolver import input_applies
from engine.reference.standards_reader import StandardsReader
from models.execution import ExecutionPlan
from models.graph import EdgeType, GraphEdge, GraphVersion
from models.input import EngineeringInput, ParameterDescriptor
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


from engine.graph.conditions import GraphCycleError, when_clause_matches
from engine.graph.micro_graph_engine import MicroGraphEngine


class GraphTraversalError(Exception):
    """Raised when a workflow cannot be resolved via the micro-graph."""


def legacy_graph_traversal_enabled(reader: StandardsReader) -> bool:
    """Return True when legacy depends_on traversal is permitted."""
    import os

    flag = os.environ.get("VER03_LEGACY_GRAPH_TRAVERSAL", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    return not reader.graph_store.available


# Legacy workflow slug → micro-graph workflow node id (resolved at execution time only)
_LEGACY_ROOT_ALIASES: dict[str, str] = {
    "pipe_wall_thickness_design": "B313-WF-PIPE-WALL-THICKNESS",
    "mawp_design": "B313-WF-MAWP",
    "B313-PIPE-WALL-THICKNESS-DESIGN": "B313-WF-PIPE-WALL-THICKNESS",
}


def normalize_root_id(root_ref: str) -> str:
    """Convert root path references to workflow slug ids."""
    text = root_ref.strip().strip("/")
    if text.endswith("root.md"):
        text = text[: -len("root.md")].strip("/")
    if text.startswith("tasks/"):
        text = text[len("tasks/") :].strip("/")
    if text.startswith("roots/"):
        text = text[len("roots/") :].strip("/")
    if not text:
        return root_ref
    return text.split("/")[-1]


def resolve_workflow_node_id(root_ref: str) -> str:
    """Map legacy slug to micro-graph workflow node id when applicable."""
    slug = normalize_root_id(root_ref)
    return _LEGACY_ROOT_ALIASES.get(slug, slug)


class GraphEngine:
    """Build deterministic execution plans from standards node dependencies."""

    def _micro_engine(self, reader: StandardsReader) -> MicroGraphEngine | None:
        store = reader.graph_store
        engine = MicroGraphEngine(store)
        if engine.available:
            return engine
        return None

    def _resolve_micro_root(self, root_id: str, reader: StandardsReader) -> str:
        slug = normalize_root_id(root_id)
        micro = self._micro_engine(reader)
        if micro is None:
            return resolve_workflow_node_id(slug)
        resolved_slug = resolve_workflow_node_id(slug)
        if micro.store.get_node(resolved_slug) is not None:
            return resolved_slug
        if micro.store.get_node(slug) is not None:
            return slug
        resolved = micro.store.resolve_node_id(resolved_slug)
        return resolved or resolved_slug

    def uses_micro_graph(self, reader: StandardsReader, root_id: str) -> bool:
        micro = self._micro_engine(reader)
        if micro is None:
            return False
        resolved = self._resolve_micro_root(root_id, reader)
        node = micro.store.get_node(resolved)
        return node is not None and node.node_type == "workflow"

    def _resolve_plan(
        self,
        *,
        root_id: str,
        reader: StandardsReader,
        inputs: dict[str, EngineeringInput],
        plan: ExecutionPlan | None = None,
    ) -> ExecutionPlan:
        if plan is not None:
            return plan
        slug = normalize_root_id(root_id)
        return self.build_plan(
            task_id="preview",
            root_id=slug,
            inputs=inputs,
            reader=reader,
        )

    @staticmethod
    def _expansion_inputs_ready(inputs: dict[str, EngineeringInput] | None) -> bool:
        data = inputs or {}
        for field_name in ("straight_pipe_section", "pressure_loading"):
            if field_value(field_name, data) is None:
                return False
        return True

    def build_plan(
        self,
        *,
        task_id: str,
        root_id: str,
        inputs: dict[str, EngineeringInput],
        reader: StandardsReader,
        lazy: bool = False,
    ) -> ExecutionPlan:
        slug = normalize_root_id(root_id)
        micro = self._micro_engine(reader)
        if micro is not None and self.uses_micro_graph(reader, slug):
            resolved = self._resolve_micro_root(slug, reader)
            return micro.build_plan(
                task_id=task_id,
                root_id=resolved,
                inputs=inputs,
                lazy=lazy,
            )

        if not legacy_graph_traversal_enabled(reader):
            raise GraphTraversalError(
                f"Workflow '{slug}' was not found in the compiled micro-graph. "
                "Rebuild graph caches with scripts/build_graph_db.py or set "
                "VER03_LEGACY_GRAPH_TRAVERSAL=1 for legacy depends_on traversal."
            )

        root_record = reader.load(slug)
        nodes_set: set[str] = set()
        edges: list[GraphEdge] = []
        node_versions: dict[str, str] = {}
        skipped_nodes: list[dict[str, str]] = []

        self._collect_nodes(
            slug,
            reader,
            nodes_set,
            edges,
            node_versions,
            visiting=set(),
            inputs=inputs,
            skipped_nodes=skipped_nodes,
        )

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
            skipped_nodes=tuple(skipped_nodes),
        )

    def discover_roots(
        self,
        reader: StandardsReader,
        *,
        workflow: str | None = None,
        keywords: list[str] | None = None,
    ) -> list[WorkflowCandidate]:
        """Scan workflow nodes and return candidates ranked by match confidence."""
        micro = self._micro_engine(reader)
        if micro is not None and micro.store.list_workflows():
            return micro.discover_roots(workflow=workflow, keywords=keywords)

        candidates: list[WorkflowCandidate] = []
        keyword_text = " ".join(keywords or []).lower()

        for path in sorted(reader.tasks_dir.glob("*/root.md")):
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
                        standard=reader.standard,
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

    def list_workflows(self, reader: StandardsReader) -> list[dict[str, Any]]:
        micro = self._micro_engine(reader)
        if micro is not None and micro.store.list_workflows():
            return micro.list_workflows()
        return []

    def get_neighbors(
        self,
        reader: StandardsReader,
        node_id: str,
        *,
        depth: int = 1,
        edge_types: set[str] | None = None,
    ) -> dict[int, list[str]]:
        micro = self._micro_engine(reader)
        if micro is None:
            return {0: [node_id]}
        return micro.get_neighbors(node_id, depth=depth, edge_types=edge_types)

    def resolve_next_step(
        self,
        root_id: str,
        reader: StandardsReader,
        inputs: dict[str, EngineeringInput],
    ) -> dict[str, Any] | None:
        slug = normalize_root_id(root_id)
        micro = self._micro_engine(reader)
        if micro is None or not self.uses_micro_graph(reader, slug):
            return None
        resolved = self._resolve_micro_root(slug, reader)
        return micro.resolve_next_step(resolved, inputs)

    def prefetch(
        self,
        reader: StandardsReader,
        *,
        task_id: str,
        root_id: str,
        inputs: dict[str, EngineeringInput],
        horizon: int = 1,
    ) -> None:
        slug = normalize_root_id(root_id)
        micro = self._micro_engine(reader)
        if micro is None or not self.uses_micro_graph(reader, slug):
            return
        resolved = self._resolve_micro_root(slug, reader)
        micro.prefetch(task_id=task_id, root_id=resolved, inputs=inputs, horizon=horizon)

    def expansion_gate_ready(
        self,
        root_id: str,
        reader: StandardsReader,
        *,
        existing_inputs: dict[str, EngineeringInput] | None = None,
    ) -> bool:
        """Return True when expansion assumptions are satisfied."""
        slug = normalize_root_id(root_id)
        micro = self._micro_engine(reader)
        if micro is not None and self.uses_micro_graph(reader, slug):
            resolved = self._resolve_micro_root(slug, reader)
            return micro.expansion_gate_ready(resolved, existing_inputs or {})
        inputs = existing_inputs or {}
        evaluation = self.evaluate_assumptions(root_id, reader, existing_inputs=inputs)
        if evaluation.is_blocked:
            return False
        for field_name in ("straight_pipe_section", "pressure_loading"):
            if field_name in evaluation.missing_fields:
                return False
            if field_value(field_name, inputs) is None:
                return False
        return True

    def seed_parameter_registry(
        self,
        root_id: str,
        reader: StandardsReader,
        *,
        existing_inputs: dict[str, EngineeringInput] | None = None,
    ) -> dict[str, ParameterDescriptor]:
        """Build parameter registry descriptors from graph parameter nodes."""
        slug = normalize_root_id(root_id)
        micro = self._micro_engine(reader)
        if micro is not None and self.uses_micro_graph(reader, slug):
            resolved = self._resolve_micro_root(slug, reader)
            return micro.seed_parameter_registry(resolved, existing_inputs or {})
        if not legacy_graph_traversal_enabled(reader):
            return {}
        if not self.expansion_gate_ready(slug, reader, existing_inputs=existing_inputs):
            return {}
        plan = self.build_plan(
            task_id="preview",
            root_id=slug,
            inputs=existing_inputs or {},
            reader=reader,
        )
        return seed_parameter_registry(
            reader,
            execution_order=plan.execution_order,
            existing_inputs=existing_inputs,
        )

    def required_user_inputs(
        self,
        root_id: str,
        reader: StandardsReader,
        *,
        existing_inputs: set[str] | None = None,
        task_inputs: dict[str, EngineeringInput] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> list[str]:
        """Collect required user-provided inputs for a workflow root (no execution)."""
        slug = normalize_root_id(root_id)
        micro = self._micro_engine(reader)
        if micro is not None and self.uses_micro_graph(reader, slug):
            resolved = self._resolve_micro_root(slug, reader)
            return micro.required_user_inputs(resolved, task_inputs or {})
        inputs = task_inputs or {}
        if plan is None:
            if not self.expansion_gate_ready(slug, reader, existing_inputs=inputs):
                return []
        elif not self._expansion_inputs_ready(inputs):
            return []
        resolved_plan = self._resolve_plan(
            root_id=slug,
            reader=reader,
            inputs=inputs,
            plan=plan,
        )
        existing = existing_inputs or set()
        required: list[str] = []
        seen: set[str] = set()

        for node_id in resolved_plan.execution_order:
            record = reader.load(node_id)
            if str(record.metadata.get("type", "")) == "root":
                continue
            for spec in record.metadata.get("inputs", []) or []:
                if not isinstance(spec, dict):
                    continue
                if not input_applies(spec, task_inputs or {}):
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

    def evaluate_assumptions(
        self,
        root_id: str,
        reader: StandardsReader,
        *,
        existing_inputs: dict[str, EngineeringInput] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> AssumptionEvaluation:
        """Check expansion assumptions along the filtered workflow path."""
        slug = normalize_root_id(root_id)
        micro = self._micro_engine(reader)
        if micro is not None and self.uses_micro_graph(reader, slug):
            resolved = self._resolve_micro_root(slug, reader)
            return micro.evaluate_assumptions(resolved, existing_inputs or {})
        inputs = existing_inputs or {}
        resolved_plan = self._resolve_plan(
            root_id=slug,
            reader=reader,
            inputs=inputs,
            plan=plan,
        )
        evaluation = evaluate_path_expansion_assumptions(
            resolved_plan.execution_order,
            reader,
            existing_inputs=inputs,
        )
        root_interactions = collect_root_interactions(reader, slug)
        path_interactions = collect_path_interactions(reader, resolved_plan.execution_order)
        for skipped in resolved_plan.skipped_nodes:
            if not skipped.get("pending"):
                continue
            field_name = str(skipped.get("field", ""))
            if not field_name or field_name in evaluation.missing_fields:
                continue
            evaluation.missing_fields.append(field_name)
            evaluation.field_nodes[field_name] = str(skipped.get("node_id", ""))
            interaction = find_interaction(path_interactions, field_name)
            if interaction is None:
                interaction = find_interaction(root_interactions, field_name)
            if interaction is not None:
                evaluation.field_questions[field_name] = question_for_interaction(interaction)
            else:
                evaluation.field_questions[field_name] = question_for(
                    NodeAssumptionSpec(
                        id="pressure_loading_case",
                        description="Confirm pressure loading case",
                        field=field_name,
                    )
                )
        return evaluation

    def resolve_and_propose_path_inputs(
        self,
        root_id: str,
        reader: StandardsReader,
        *,
        existing_inputs: dict[str, EngineeringInput] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> dict[str, EngineeringInput]:
        """Propose default values for value-resolution specs on the active path."""
        slug = normalize_root_id(root_id)
        resolved_plan = self._resolve_plan(
            root_id=slug,
            reader=reader,
            inputs=existing_inputs or {},
            plan=plan,
        )
        specs = collect_path_interactions(reader, resolved_plan.execution_order)
        proposed = propose_default_values(specs, existing_inputs or {})
        proposed.update(propose_decision_defaults(specs, existing_inputs or {}))
        from engine.reference.coefficient_resolver import propose_coefficient_defaults
        from models.input import proposed_default_input

        coeff_defaults = propose_coefficient_defaults(
            reader.pack_root,
            existing_inputs=existing_inputs or {},
        )
        for input_id, (value, condition) in coeff_defaults.items():
            if input_id in (existing_inputs or {}) or input_id in proposed:
                continue
            proposed[input_id] = proposed_default_input(
                input_id,
                value,
                unit="dimensionless",
                default=value,
                default_condition=condition,
            )
        proposed.update(self._propose_provisional_assumptions(reader, resolved_plan.execution_order, existing_inputs or {}))
        return proposed

    @staticmethod
    def _propose_provisional_assumptions(
        reader: StandardsReader,
        execution_order: tuple[str, ...] | list[str],
        existing_inputs: dict[str, EngineeringInput],
    ) -> dict[str, EngineeringInput]:
        """Propose thin_wall and other provisional assumptions from node metadata."""
        from models.input import InputSource, InputStatus, ResolutionMethod

        proposed: dict[str, EngineeringInput] = {}
        for node_id in execution_order:
            record = reader.load(node_id)
            for item in record.metadata.get("provisional_assumptions", []) or []:
                if not isinstance(item, dict):
                    continue
                field_name = str(item.get("field", ""))
                if not field_name or field_name in existing_inputs:
                    continue
                default = item.get("default", True)
                proposed[field_name] = EngineeringInput(
                    input_id=field_name,
                    value=default,
                    unit="dimensionless",
                    source=InputSource.SYSTEM,
                    status=InputStatus.CONFIRMED,
                    description=str(item.get("description", "")),
                    introduced_at_node=record.node_id,
                    resolution_method=ResolutionMethod.SYSTEM,
                )
        return proposed

    def evaluate_expansion_interactions(
        self,
        root_id: str,
        reader: StandardsReader,
        *,
        existing_inputs: dict[str, EngineeringInput] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> AssumptionEvaluation:
        """Check value confirmations required before full path expansion."""
        from engine.graph.node_interaction import InteractionEvaluation

        slug = normalize_root_id(root_id)
        inputs = existing_inputs or {}
        resolved_plan = self._resolve_plan(
            root_id=slug,
            reader=reader,
            inputs=inputs,
            plan=plan,
        )
        specs = collect_path_interactions(reader, resolved_plan.execution_order)
        interaction_eval: InteractionEvaluation = evaluate_pending_interactions(
            specs,
            existing_inputs or {},
            phase="expansion",
        )
        evaluation = AssumptionEvaluation()
        for field_id in interaction_eval.missing_fields:
            evaluation.missing_fields.append(field_id)
            evaluation.field_nodes[field_id] = interaction_eval.field_nodes[field_id]
            evaluation.field_questions[field_id] = interaction_eval.field_questions[field_id]
        return evaluation

    def expansion_ready_nodes(
        self,
        node_ids: list[str] | tuple[str, ...],
        reader: StandardsReader,
        *,
        existing_inputs: dict[str, EngineeringInput] | None = None,
    ) -> list[str]:
        """Return node ids whose value requirements are confirmed for expansion."""
        inputs = existing_inputs or {}
        ready: list[str] = []
        for node_id in node_ids:
            record = reader.load(node_id)
            if str(record.metadata.get("type", "")) == "root":
                ready.append(node_id)
                continue
            if node_expansion_ready(record, inputs, reader=reader):
                ready.append(node_id)
        return ready

    def evaluate_execution_assumptions(
        self,
        root_id: str,
        reader: StandardsReader,
        *,
        existing_inputs: dict[str, EngineeringInput] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> AssumptionEvaluation:
        """Check execution assumptions for nodes on the filtered workflow path."""
        from engine.graph.assumption_checker import evaluate_path_execution_assumptions

        slug = normalize_root_id(root_id)
        inputs = existing_inputs or {}
        resolved_plan = self._resolve_plan(
            root_id=slug,
            reader=reader,
            inputs=inputs,
            plan=plan,
        )
        return evaluate_path_execution_assumptions(
            resolved_plan.execution_order,
            reader,
            existing_inputs=inputs,
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
        inputs: dict[str, EngineeringInput],
        skipped_nodes: list[dict[str, str]],
    ) -> None:
        if node_id in visiting:
            raise GraphCycleError(f"Dependency cycle detected at node: {node_id}")

        record = reader.load(node_id)
        nodes.add(record.node_id)
        node_versions[record.node_id] = str(record.metadata.get("version", "1.0"))
        visiting.add(record.node_id)

        for item in record.metadata.get("depends_on", []) or []:
            if isinstance(item, dict):
                dep_id = str(item.get("node_id", ""))
                if not dep_id:
                    continue
                when = item.get("when") if isinstance(item.get("when"), dict) else None
                if not when_clause_matches(when, inputs):
                    reason = "conditional dependency not active"
                    pending = False
                    if when:
                        field_name = str(when.get("field", ""))
                        if field_name and field_value(field_name, inputs) is None:
                            pending = True
                            reason = f"when {field_name} in {when.get('in')} not satisfied (field missing)"
                        else:
                            reason = (
                                f"when {when.get('field')} in {when.get('in')} not satisfied"
                            )
                    skipped_nodes.append(
                        {
                            "node_id": dep_id,
                            "reason": reason,
                            "field": str(when.get("field", "")) if when else "",
                            "pending": pending,
                        }
                    )
                    continue
                raw_type = str(item.get("dependency_type", "dependency"))
            elif isinstance(item, str):
                dep_id = item
                raw_type = "dependency"
            else:
                continue

            try:
                dep_type = EdgeType(raw_type)
            except ValueError:
                dep_type = EdgeType.DEPENDENCY

            if dep_type == EdgeType.REFERENCE and dep_id in nodes:
                continue

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
                inputs=inputs,
                skipped_nodes=skipped_nodes,
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
