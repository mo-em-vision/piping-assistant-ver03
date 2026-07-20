"""Micro-graph workflow engine facade."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.graph.assumption_checker import (
    AssumptionEvaluation,
    _merge_evaluations,
    evaluate_metadata_expansion_assumptions,
    field_value,
)
from engine.graph.conditions import when_clause_matches
from engine.presentation.graph_display_blocks import emit_initiation_blocks
from engine.graph.graph_store import GraphStore
from engine.graph.lazy_expander import (
    ExpansionState,
    _node_active_on_path,
    expand_workflow,
    expansion_gate_ready,
    next_pending_parameter,
)
from engine.graph.lookup_parameter_resolution import (
    parameter_resolution_for_parameter,
    prerequisite_input_keys,
)
from engine.graph.param_priority import parameter_collection_priority, parameter_concept_id, parameter_defined_in
from engine.graph.prefetch import prefetch_async
from engine.reference.node_types import is_ui_parameter, parameter_input_id
from engine.reference.parameter_metadata import parameter_prompt_or_description, prepare_parameter_metadata
from engine.units.unit_ids import symbol_from_unit_id
from engine.graph.traversal import bfs_neighbors, topological_order
from engine.reference.graph_edge_schema import workflow_anchor_target
from engine.reference.graph_db import GraphEdgeRecord
from models.execution import ExecutionPlan
from models.graph import EdgeType, GraphEdge, GraphVersion
from models.fact import Fact
from models.input import ParameterDescriptor
from models.planning import WorkflowCandidate


def _append_missing_input_keys(
    store: GraphStore,
    *,
    keys: list[str],
    required: list[str],
    seen: set[str],
    inputs: dict[str, Fact],
) -> None:
    for key in keys:
        for key_name in prerequisite_input_keys(store, str(key)):
            if not key_name or key_name in seen:
                continue
            if field_value(key_name, inputs) is not None:
                continue
            seen.add(key_name)
            required.append(key_name)


def _sort_required_inputs(
    store: GraphStore,
    required: list[str],
    active_nodes: set[str],
) -> list[str]:
    from engine.reference.parameter_keys import param_node_id_for_input

    def sort_key(fact_key: str) -> tuple[int, str]:
        param_id = param_node_id_for_input(fact_key)
        if param_id and store.get_node(param_id) is not None:
            priority = parameter_collection_priority(store, param_id, active_nodes)
        else:
            priority = 100
        return (priority, fact_key)

    return sorted(required, key=sort_key)


from engine.graph.workflow_adapters import DEFINITION_PHASE_INPUTS as _DEFINITION_PHASE_INPUTS


def _edges_from_plan(plan: ExecutionPlan) -> list[GraphEdgeRecord]:
    edges: list[GraphEdgeRecord] = []
    for edge in plan.dependencies:
        edge_type = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
        edges.append(
            GraphEdgeRecord(
                from_id=edge.from_node,
                to_id=edge.to_node,
                edge_type=edge_type,
                metadata={},
            )
        )
    return edges


def _assumption_scan_ids(store: GraphStore, root_id: str, seed_nodes: list[str]) -> list[str]:
    scan_ids = list(seed_nodes)
    wf = store.get_node(root_id)
    if wf is None:
        return scan_ids
    for edge in store.outgoing(
        root_id,
        edge_types={"requires", "requires_parameter", "contains", "contains_paragraph"},
    ):
        if edge.to_id not in scan_ids:
            scan_ids.append(edge.to_id)
    anchors = workflow_anchor_target(wf.metadata)
    if isinstance(anchors, str):
        for edge in store.outgoing(anchors, edge_types={"contains", "contains_paragraph"}):
            if edge.to_id not in scan_ids:
                scan_ids.append(edge.to_id)
    return scan_ids


def _collect_pending_assumptions(
    store: GraphStore,
    node_ids: list[str],
    inputs: dict[str, Fact],
) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    for node_id in node_ids:
        node = store.get_node(node_id)
        if node is None:
            continue
        if is_ui_parameter(node.metadata, node.node_type):
            field_name = parameter_input_id(node.metadata)
            if field_name and field_value(field_name, inputs) is None:
                pending.append(
                    {
                        "field": field_name,
                        "node_id": node_id,
                        "question": parameter_prompt_or_description(node.metadata) or "",
                    }
                )
    return pending


def _resolution_method(resolution: Any) -> str:
    if isinstance(resolution, list):
        resolution = resolution[0] if resolution else {}
    if isinstance(resolution, dict):
        return str(resolution.get("method", "user_input"))
    return "user_input"


def _resolution_keys(resolution: Any) -> list[str]:
    if isinstance(resolution, list):
        resolution = resolution[0] if resolution else {}
    if not isinstance(resolution, dict):
        return []
    keys = resolution.get("keys") or []
    return [str(key) for key in keys if str(key).strip()]


def _nomenclature_applies(
    item: dict[str, Any],
    *,
    active_nodes: tuple[str, ...] | list[str],
) -> bool:
    resolution = item.get("resolution") or {}
    if isinstance(resolution, list):
        for spec in resolution:
            if isinstance(spec, dict) and when_clause_matches(spec.get("when"), {}):
                resolution = spec
                break
        else:
            resolution = resolution[0] if resolution else {}
    if not isinstance(resolution, dict):
        return True
    when_nodes = resolution.get("required_when_nodes") or []
    if when_nodes and not any(str(node_id) in active_nodes for node_id in when_nodes):
        return False
    return True


def _parameter_required_on_active_path(
    store: GraphStore,
    param_node_id: str,
    active_nodes: set[str],
    inputs: dict[str, Fact],
) -> bool:
    """Return True when an active equation/lookup/validation producer requires this parameter."""
    from engine.graph.lazy_expander import _node_active_on_path
    from engine.reference.relationship_taxonomy import REQUIRES_TRAVERSAL_TYPES

    producer_types = frozenset({"equation", "lookup", "validation_rule", "calculation"})
    saw_requirement = False
    for edge in store.incoming(param_node_id, edge_types=REQUIRES_TRAVERSAL_TYPES):
        producer_id = edge.from_id
        if store.node_type(producer_id) not in producer_types:
            continue
        edge_when = edge.metadata.get("when") if edge.metadata else None
        if isinstance(edge_when, dict) and not when_clause_matches(edge_when, inputs):
            saw_requirement = True
            continue
        saw_requirement = True
        if producer_id not in active_nodes:
            continue
        if _node_active_on_path(store, producer_id, inputs):
            return True
    if saw_requirement:
        return False
    return True


def _append_nomenclature_user_inputs(
    store: GraphStore,
    *,
    active_nodes: tuple[str, ...] | list[str],
    inputs: dict[str, Fact],
    required: list[str],
    seen: set[str],
) -> None:
    for node_id in active_nodes:
        node = store.get_node(node_id)
        if node is None or node.node_type != "paragraph":
            continue
        for item in node.metadata.get("nomenclature", []) or []:
            if not isinstance(item, dict) or not item.get("introduced_here"):
                continue
            if not _nomenclature_applies(item, active_nodes=active_nodes):
                continue
            input_id = str(item.get("input_id") or "").strip()
            if not input_id or input_id in seen or input_id in _DEFINITION_PHASE_INPUTS:
                continue
            resolution = item.get("resolution")
            method = _resolution_method(resolution)
            if method == "user_input" and field_value(input_id, inputs) is None:
                seen.add(input_id)
                required.append(input_id)
            elif method == "table_lookup" and field_value(input_id, inputs) is None:
                for key_name in _resolution_keys(resolution):
                    if key_name not in seen and field_value(key_name, inputs) is None:
                        seen.add(key_name)
                        required.append(key_name)


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
        from engine.graph.root_discovery import (
            broad_discovery_confidence,
            is_specific_lookup,
            workflow_lookup_confidence,
        )

        candidates: list[WorkflowCandidate] = []
        keyword_text = " ".join(keywords or []).lower()
        specific_lookup = is_specific_lookup(workflow)
        for node in self._store.list_workflows():
            workflow_id = str(node.metadata.get("slug") or node.node_id)
            intent = str(node.metadata.get("engineering_intent", "") or "")
            title = str(node.metadata.get("title", node.node_id))
            purpose = str(node.metadata.get("purpose", "") or "")

            if specific_lookup:
                confidence = workflow_lookup_confidence(
                    workflow or "",
                    slug=workflow_id,
                    intent=intent,
                    node_id=node.node_id,
                )
                if confidence <= 0.0:
                    continue
            else:
                confidence = broad_discovery_confidence(
                    keyword_text=keyword_text,
                    intent=intent,
                    title=title,
                    slug=workflow_id,
                    node_id=node.node_id,
                    purpose=purpose,
                )

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
        inputs: dict[str, Fact],
        *,
        lazy: bool = True,
    ) -> ExpansionState:
        return expand_workflow(self._store, root_id, inputs, lazy=lazy)

    def build_plan(
        self,
        *,
        task_id: str,
        root_id: str,
        inputs: dict[str, Fact],
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
        inputs: dict[str, Fact],
    ) -> dict[str, Any]:
        expansion = expand_workflow(self._store, root_id, inputs, lazy=True)
        scan_ids = _assumption_scan_ids(self._store, root_id, list(expansion.active_nodes))
        pending_assumptions = _collect_pending_assumptions(self._store, scan_ids, inputs)

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
        inputs: dict[str, Fact],
        *,
        plan: ExecutionPlan | None = None,
    ) -> AssumptionEvaluation:
        evaluation = AssumptionEvaluation()
        if plan is not None:
            scan_ids = _assumption_scan_ids(self._store, root_id, list(plan.nodes))
            pending_assumptions = _collect_pending_assumptions(self._store, scan_ids, inputs)
        else:
            pending_assumptions = self.resolve_next_step(root_id, inputs)["pending_assumptions"]
        for item in pending_assumptions:
            field_name = str(item["field"])
            evaluation.missing_fields.append(field_name)
            evaluation.field_nodes[field_name] = str(item["node_id"])
            evaluation.field_questions[field_name] = str(item.get("question", ""))

        wf = self._store.get_node(root_id)
        if wf is not None:
            evaluation = _merge_evaluations(
                evaluation,
                evaluate_metadata_expansion_assumptions(
                    wf.metadata,
                    node_id=root_id,
                    existing_inputs=inputs,
                ),
            )
            anchors = workflow_anchor_target(wf.metadata)
            if isinstance(anchors, str):
                anchor_node = self._store.get_node(anchors)
                if anchor_node is not None:
                    evaluation = _merge_evaluations(
                        evaluation,
                        evaluate_metadata_expansion_assumptions(
                            anchor_node.metadata,
                            node_id=anchors,
                            existing_inputs=inputs,
                        ),
                    )
        if plan is not None:
            for node_id in plan.execution_order:
                node = self._store.get_node(node_id)
                if node is None or node.node_type != "paragraph":
                    continue
                evaluation = _merge_evaluations(
                    evaluation,
                    evaluate_metadata_expansion_assumptions(
                        node.metadata,
                        node_id=node_id,
                        existing_inputs=inputs,
                    ),
                )
        return evaluation

    def expansion_gate_ready(
        self,
        root_id: str,
        inputs: dict[str, Fact],
    ) -> bool:
        return expansion_gate_ready(self._store, root_id, inputs)

    def seed_parameter_registry(
        self,
        root_id: str,
        inputs: dict[str, Fact],
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
            input_id = str(node.metadata.get("input_id") or node.metadata.get("key") or "").strip()
            if not input_id or input_id in registry:
                continue
            param_meta = prepare_parameter_metadata(node.metadata)
            defined_in = parameter_defined_in(param_meta)
            symbol = str(param_meta.get("symbol") or "").strip()
            description = str(
                param_meta.get("title") or param_meta.get("description") or symbol or ""
            ).strip()
            unit = str(param_meta.get("unit") or "").strip()
            if not unit:
                canonical_unit = str(param_meta.get("canonical_unit") or "").strip()
                if canonical_unit:
                    unit = symbol_from_unit_id(canonical_unit)
            registry[input_id] = ParameterDescriptor(
                input_id=input_id,
                symbol=symbol,
                description=description,
                introduced_at_node=defined_in[0] if defined_in else node_id,
                unit=unit,
                defined_in_nodes=defined_in,
                concept_id=parameter_concept_id(param_meta),
            )
        return registry

    def required_user_inputs(
        self,
        root_id: str,
        inputs: dict[str, Fact],
        *,
        plan: ExecutionPlan | None = None,
    ) -> list[str]:
        if not expansion_gate_ready(self._store, root_id, inputs):
            return []
        if plan is not None:
            active_nodes = set(plan.nodes)
            node_iter = list(plan.nodes)
        else:
            expansion = expand_workflow(self._store, root_id, inputs, lazy=False)
            active_nodes = set(expansion.active_nodes)
            node_iter = expansion.active_nodes
        required: list[str] = []
        seen: set[str] = set()
        for node_id in node_iter:
            node = self._store.get_node(node_id)
            if node is None or node.node_type != "parameter":
                continue
            if is_ui_parameter(node.metadata, node.node_type):
                continue
            if str(node.metadata.get("parameter_class", "")) == "calculated_quantity":
                continue
            if self._store.incoming(node_id, edge_types={"calculates_parameter"}):
                continue
            if not _parameter_required_on_active_path(self._store, node_id, active_nodes, inputs):
                continue
            if not _node_active_on_path(self._store, node_id, inputs):
                continue
            input_id = str(node.metadata.get("input_id") or node.metadata.get("key") or "").strip()
            if not input_id or input_id in seen or input_id in _DEFINITION_PHASE_INPUTS:
                continue
            resolution = parameter_resolution_for_parameter(
                self._store,
                node_id,
                active_nodes=active_nodes,
                inputs=inputs,
            ) or {}
            method = str(resolution.get("method", "user_input")) if isinstance(resolution, dict) else "user_input"
            if method == "branch_choice" and input_id not in seen:
                seen.add(input_id)
                required.append(input_id)
            elif method == "user_input" and field_value(input_id, inputs) is None:
                seen.add(input_id)
                required.append(input_id)
            elif method == "table_lookup" and field_value(input_id, inputs) is None:
                # Require lookup key parameters, not the looked-up symbol itself.
                from engine.graph.lookup_parameter_resolution import param_node_id_for_fact_key

                lookup_keys: list[str] = []
                for key in (resolution.get("keys") or []):
                    key_name = str(key).strip()
                    if not key_name:
                        continue
                    param_id = param_node_id_for_fact_key(self._store, key_name)
                    if param_id and not _parameter_required_on_active_path(
                        self._store, param_id, active_nodes, inputs
                    ):
                        continue
                    lookup_keys.append(key_name)
                _append_missing_input_keys(
                    self._store,
                    keys=lookup_keys,
                    required=required,
                    seen=seen,
                    inputs=inputs,
                )
            elif method == "material_catalog":
                _append_missing_input_keys(
                    self._store,
                    keys=[input_id],
                    required=required,
                    seen=seen,
                    inputs=inputs,
                )
        _append_nomenclature_user_inputs(
            self._store,
            active_nodes=node_iter,
            inputs=inputs,
            required=required,
            seen=seen,
        )
        return _sort_required_inputs(self._store, required, active_nodes)

    def prefetch(self, *, task_id: str, root_id: str, inputs: dict[str, Fact], horizon: int = 1) -> None:
        prefetch_async(self._store, task_id=task_id, root_id=root_id, inputs=inputs, horizon=horizon)

    def question_for_field(self, field_name: str) -> str | None:
        for node in self._store.list_nodes():
            if node.node_type != "parameter":
                continue
            field = parameter_input_id(node.metadata)
            if field == field_name:
                return parameter_prompt_or_description(node.metadata) or ""
        return None

    def collect_active_edges(
        self,
        root_id: str,
        inputs: dict[str, Fact],
    ) -> list[GraphEdgeRecord]:
        expansion = expand_workflow(self._store, root_id, inputs, lazy=False)
        return list(expansion.edges)
