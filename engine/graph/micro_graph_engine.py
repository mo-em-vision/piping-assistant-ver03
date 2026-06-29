"""Micro-graph workflow engine facade."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.graph.assumption_checker import AssumptionEvaluation, field_value
from engine.graph.conditions import when_clause_matches
from engine.graph.display_emitter import emit_initiation_blocks
from engine.graph.graph_store import GraphStore
from engine.graph.lazy_expander import (
    ExpansionState,
    expand_workflow,
    expansion_gate_ready,
    next_pending_parameter,
)
from engine.graph.param_priority import parameter_collection_priority, parameter_concept_id, parameter_defined_in
from engine.graph.prefetch import prefetch_async
from engine.reference.node_types import is_ui_parameter, parameter_input_id
from engine.graph.traversal import bfs_neighbors, topological_order
from engine.reference.graph_db import GraphEdgeRecord
from models.execution import ExecutionPlan
from models.graph import EdgeType, GraphEdge, GraphVersion
from models.input import EngineeringInput, ParameterDescriptor
from models.planning import WorkflowCandidate


_DEFINITION_PHASE_INPUTS = frozenset({"corrosion_allowance"})


class MicroGraphEngine:
    """Graph traversal over compiled micro-nodes."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    @property
    def store(self) -> GraphStore:
        return self._store

    @property
    def available(self) -> bool:
        return self._store.available

    def list_workflows(self) -> list[dict[str, Any]]:
        self._store.load()
        workflows: list[dict[str, Any]] = []
        for node in self._store.list_workflows():
            workflow_id = str(node.metadata.get("slug") or node.node_id)
            workflows.append(
                {
                    "id": workflow_id,
                    "node_id": node.node_id,
                    "name": str(node.metadata.get("title", node.node_id)),
                    "description": str(node.metadata.get("purpose", "")),
                    "discipline": "Piping",
                    "available": True,
                    "engineering_intent": node.metadata.get("engineering_intent"),
                }
            )
        return workflows

    def discover_roots(
        self,
        *,
        workflow: str | None = None,
        keywords: list[str] | None = None,
    ) -> list[WorkflowCandidate]:
        candidates: list[WorkflowCandidate] = []
        keyword_text = " ".join(keywords or []).lower()
        for node in self._store.list_workflows():
            workflow_id = str(node.metadata.get("slug") or node.node_id)
            intent = str(node.metadata.get("engineering_intent", "") or "")
            title = str(node.metadata.get("title", node.node_id))
            confidence = 0.4
            if workflow and (workflow == intent or workflow == workflow_id or workflow == node.node_id):
                confidence = 0.95
            else:
                for token in (intent, title, workflow_id, node.node_id, str(node.metadata.get("purpose", ""))):
                    if token and token.lower() in keyword_text:
                        confidence = max(confidence, 0.75)
            if confidence >= 0.4:
                candidates.append(
                    WorkflowCandidate(
                        root_id=workflow_id,
                        title=title,
                        engineering_intent=intent or None,
                        standard="asme_b31.3",
                        confidence=confidence,
                        implemented=True,
                    )
                )
        candidates.sort(key=lambda item: item.confidence, reverse=True)
        return candidates

    def get_neighbors(
        self,
        node_id: str,
        *,
        depth: int = 1,
        edge_types: set[str] | None = None,
    ) -> dict[int, list[str]]:
        return bfs_neighbors(self._store, node_id, depth=depth, edge_types=edge_types)

    def expand(
        self,
        root_id: str,
        inputs: dict[str, EngineeringInput],
        *,
        lazy: bool = True,
    ) -> ExpansionState:
        return expand_workflow(self._store, root_id, inputs, lazy=lazy)

    def build_plan(
        self,
        *,
        task_id: str,
        root_id: str,
        inputs: dict[str, EngineeringInput],
        lazy: bool = False,
    ) -> ExecutionPlan:
        expansion = expand_workflow(self._store, root_id, inputs, lazy=lazy)
        node_set = set(expansion.active_nodes)
        graph_edges: list[GraphEdge] = []
        for edge in expansion.edges:
            try:
                edge_type = EdgeType(edge.edge_type)
            except ValueError:
                edge_type = EdgeType.REQUIRES
            graph_edges.append(
                GraphEdge(
                    from_node=edge.from_id,
                    to_node=edge.to_id,
                    type=edge_type,
                    reason=edge.edge_type,
                )
            )
        execution_order = tuple(
            topological_order(
                node_set,
                expansion.edges,
                priority_key=lambda node_id: (
                    parameter_collection_priority(self._store, node_id, node_set)
                    if self._store.node_type(node_id) == "parameter"
                    else int(self._store.metadata(node_id).get("priority", 100) or 100),
                    node_id,
                ),
            )
        )
        graph_version = GraphVersion(
            graph_id=root_id,
            created=datetime.now(timezone.utc),
            standard_versions={"asme_b31.3": "1.0"},
            nodes=tuple(sorted(node_set)),
            edges=tuple(graph_edges),
        )
        return ExecutionPlan(
            task_id=task_id,
            root=root_id,
            nodes=tuple(sorted(node_set)),
            execution_order=execution_order,
            inputs=dict(inputs),
            dependencies=tuple(graph_edges),
            graph_version=graph_version,
            skipped_nodes=tuple(expansion.skipped_nodes),
        )

    def resolve_next_step(
        self,
        root_id: str,
        inputs: dict[str, EngineeringInput],
    ) -> dict[str, Any]:
        expansion = expand_workflow(self._store, root_id, inputs, lazy=True)
        pending_assumptions: list[dict[str, Any]] = []

        wf = self._store.get_node(root_id)
        scan_ids = list(expansion.active_nodes)
        if wf is not None:
            for edge in self._store.outgoing(root_id, edge_types={"requires", "contains"}):
                if edge.to_id not in scan_ids:
                    scan_ids.append(edge.to_id)
            anchors = wf.metadata.get("anchors_to")
            if isinstance(anchors, str):
                for edge in self._store.outgoing(anchors, edge_types={"contains"}):
                    if edge.to_id not in scan_ids:
                        scan_ids.append(edge.to_id)

        for node_id in scan_ids:
            node = self._store.get_node(node_id)
            if node is None:
                continue
            if is_ui_parameter(node.metadata, node.node_type):
                field_name = parameter_input_id(node.metadata)
                if field_name and field_value(field_name, inputs) is None:
                    pending_assumptions.append(
                        {
                            "field": field_name,
                            "node_id": node_id,
                            "question": node.metadata.get("question", ""),
                        }
                    )

        next_param = next_pending_parameter(self._store, expansion, inputs)
        return {
            "expansion": expansion,
            "pending_assumptions": pending_assumptions,
            "next_parameter": next_param,
            "initiation_blocks": emit_initiation_blocks(self._store, root_id),
        }

    def evaluate_assumptions(
        self,
        root_id: str,
        inputs: dict[str, EngineeringInput],
    ) -> AssumptionEvaluation:
        evaluation = AssumptionEvaluation()
        step = self.resolve_next_step(root_id, inputs)
        for item in step["pending_assumptions"]:
            field_name = str(item["field"])
            evaluation.missing_fields.append(field_name)
            evaluation.field_nodes[field_name] = str(item["node_id"])
            evaluation.field_questions[field_name] = str(item.get("question", ""))
        return evaluation

    def expansion_gate_ready(
        self,
        root_id: str,
        inputs: dict[str, EngineeringInput],
    ) -> bool:
        return expansion_gate_ready(self._store, root_id, inputs)

    def seed_parameter_registry(
        self,
        root_id: str,
        inputs: dict[str, EngineeringInput],
    ) -> dict[str, ParameterDescriptor]:
        if not expansion_gate_ready(self._store, root_id, inputs):
            return {}
        expansion = expand_workflow(self._store, root_id, inputs, lazy=False)
        registry: dict[str, ParameterDescriptor] = {}
        for node_id in expansion.active_nodes:
            node = self._store.get_node(node_id)
            if node is None or node.node_type != "parameter":
                continue
            if is_ui_parameter(node.metadata, node.node_type):
                continue
            input_id = str(node.metadata.get("input_id", ""))
            if not input_id or input_id in registry:
                continue
            defined_in = parameter_defined_in(node.metadata)
            registry[input_id] = ParameterDescriptor(
                input_id=input_id,
                symbol=str(node.metadata.get("symbol", "")),
                description=str(node.metadata.get("title") or node.metadata.get("symbol", "")),
                introduced_at_node=defined_in[0] if defined_in else node_id,
                unit=str(node.metadata.get("unit", "")),
                defined_in_nodes=defined_in,
                concept_id=parameter_concept_id(node.metadata),
            )
        return registry

    def required_user_inputs(
        self,
        root_id: str,
        inputs: dict[str, EngineeringInput],
    ) -> list[str]:
        if not expansion_gate_ready(self._store, root_id, inputs):
            return []
        expansion = expand_workflow(self._store, root_id, inputs, lazy=False)
        required: list[str] = []
        seen: set[str] = set()
        for node_id in expansion.active_nodes:
            node = self._store.get_node(node_id)
            if node is None or node.node_type != "parameter":
                continue
            if is_ui_parameter(node.metadata, node.node_type):
                continue
            input_id = str(node.metadata.get("input_id", ""))
            if not input_id or input_id in seen or input_id in _DEFINITION_PHASE_INPUTS:
                continue
            resolution = node.metadata.get("resolution") or {}
            method = str(resolution.get("method", "user_input")) if isinstance(resolution, dict) else "user_input"
            if method == "user_input" and field_value(input_id, inputs) is None:
                seen.add(input_id)
                required.append(input_id)
            elif method == "table_lookup" and field_value(input_id, inputs) is None:
                # Require lookup key parameters, not the looked-up symbol itself.
                for key in resolution.get("keys", []) if isinstance(resolution, dict) else []:
                    key_name = str(key)
                    if key_name not in seen and field_value(key_name, inputs) is None:
                        seen.add(key_name)
                        required.append(key_name)
        return required

    def prefetch(self, *, task_id: str, root_id: str, inputs: dict[str, EngineeringInput], horizon: int = 1) -> None:
        prefetch_async(self._store, task_id=task_id, root_id=root_id, inputs=inputs, horizon=horizon)

    def question_for_field(self, field_name: str) -> str | None:
        for node in self._store.list_nodes():
            if node.node_type != "parameter":
                continue
            field = parameter_input_id(node.metadata)
            if field == field_name:
                return str(node.metadata.get("question") or node.metadata.get("description") or "")
        return None

    def collect_active_edges(
        self,
        root_id: str,
        inputs: dict[str, EngineeringInput],
    ) -> list[GraphEdgeRecord]:
        expansion = expand_workflow(self._store, root_id, inputs, lazy=False)
        return list(expansion.edges)
