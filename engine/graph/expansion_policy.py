"""Data-driven graph expansion policy from node metadata, edges, and conditions.

Expansion must follow authored graph data (assumptions, applicability, edge ``when``
clauses, workflow navigation) — never hardcoded node ids or task field names.
"""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import (
    AssumptionEvaluation,
    evaluate_metadata_expansion_assumptions,
    expansion_assumption_fields_from_metadata,
    field_value,
    metadata_expansion_ready,
)
from engine.graph.graph_store import GraphStore
from engine.graph.traversal import dfs_collect
from engine.reference.graph_db import GraphEdgeRecord
from engine.reference.graph_edge_schema import workflow_anchor_target
from engine.reference.node_types import is_ui_parameter, parameter_input_id
from models.fact import Fact


def record_expansion_skip(
    skipped_nodes: list[dict[str, Any]],
    node_id: str,
    evaluation: AssumptionEvaluation,
) -> None:
    """Append a skip record derived from node expansion assumption evaluation."""
    if evaluation.is_blocked:
        block = evaluation.blocked[0]
        skipped_nodes.append(
            {
                "node_id": node_id,
                "reason": block.message,
                "field": block.field,
                "pending": False,
            }
        )
        return
    if evaluation.missing_fields:
        field_name = evaluation.missing_fields[0]
        skipped_nodes.append(
            {
                "node_id": node_id,
                "reason": evaluation.field_questions.get(field_name)
                or f"Expansion assumption not satisfied: {field_name}",
                "field": field_name,
                "pending": True,
            }
        )


def node_allows_child_traversal(
    store: GraphStore,
    node_id: str,
    inputs: dict[str, Fact],
) -> bool:
    """Return True when authored node assumptions permit expanding dependents."""
    node = store.get_node(node_id)
    if node is None:
        return True
    return metadata_expansion_ready(node.metadata, inputs, node_id=node_id)


def expansion_gate_evaluation(
    store: GraphStore,
    node_id: str,
    inputs: dict[str, Fact],
) -> AssumptionEvaluation:
    """Evaluate expansion assumptions for a single compiled-graph node."""
    node = store.get_node(node_id)
    if node is None:
        return AssumptionEvaluation()
    return evaluate_metadata_expansion_assumptions(
        node.metadata,
        node_id=node_id,
        existing_inputs=inputs,
    )


def expansion_projection_hint(
    store: GraphStore,
    node_id: str,
    inputs: dict[str, Fact],
) -> dict[str, Any] | None:
    """Return visualization status hints when a node blocks its own expansion."""
    evaluation = expansion_gate_evaluation(store, node_id, inputs)
    if evaluation.is_blocked:
        block = evaluation.blocked[0]
        return {
            "status": "blocked",
            "reason": block.message,
            "field": block.field,
            "pending": False,
        }
    if evaluation.missing_fields:
        field_name = evaluation.missing_fields[0]
        return {
            "status": "awaiting_expansion_assumption",
            "reason": evaluation.field_questions.get(field_name)
            or f"Expansion assumption not satisfied: {field_name}",
            "field": field_name,
            "pending": True,
        }
    return None


def _workflow_metadata(store: GraphStore, root_id: str) -> dict[str, Any]:
    for candidate in (root_id, store.resolve_node_id(root_id) or ""):
        if not candidate:
            continue
        node = store.get_node(candidate)
        if node is not None and node.node_type == "workflow":
            return node.metadata
    return store.metadata(root_id)


def collect_workflow_expansion_fields(
    store: GraphStore,
    root_id: str,
) -> list[str]:
    """Collect task fields that gate workflow expansion from graph-authored metadata."""
    fields: list[str] = []
    resolved_ids: list[str] = []
    for candidate in (root_id, store.resolve_node_id(root_id) or ""):
        if candidate and candidate not in resolved_ids:
            resolved_ids.append(candidate)

    for wf_id in resolved_ids:
        wf_node = store.get_node(wf_id)
        if wf_node is not None:
            for field_name in expansion_assumption_fields_from_metadata(wf_node.metadata):
                if field_name not in fields:
                    fields.append(field_name)

        for edge in store.outgoing(wf_id):
            if edge.edge_type not in {
                "contains",
                "contains_paragraph",
                "references",
                "starts_from_paragraph",
                "starts_from_parameter",
                "related_to",
            }:
                continue
            node = store.get_node(edge.to_id)
            if node is None:
                continue
            if is_ui_parameter(node.metadata, node.node_type):
                field_name = parameter_input_id(node.metadata)
                if field_name and field_name not in fields:
                    fields.append(field_name)

    for wf_id in resolved_ids:
        anchored = workflow_anchor_target(_workflow_metadata(store, wf_id))
        if not isinstance(anchored, str):
            continue
        anchor_node = store.get_node(anchored)
        if anchor_node is not None:
            for field_name in expansion_assumption_fields_from_metadata(anchor_node.metadata):
                if field_name not in fields:
                    fields.append(field_name)
        for edge in store.outgoing(anchored, edge_types={"contains", "contains_paragraph"}):
            node = store.get_node(edge.to_id)
            if node and is_ui_parameter(node.metadata, node.node_type):
                field_name = parameter_input_id(node.metadata)
                if field_name and field_name not in fields:
                    fields.append(field_name)

    navigation = _workflow_metadata(store, root_id).get("navigation") or {}
    for field_name in navigation.get("assumption_gate_fields") or []:
        name = str(field_name).strip()
        if name and name not in fields:
            fields.append(name)

    return fields


def workflow_expansion_gate_ready(
    store: GraphStore,
    root_id: str,
    inputs: dict[str, Fact],
) -> bool:
    """Return True when all workflow-level expansion gate fields are satisfied."""
    for field_name in collect_workflow_expansion_fields(store, root_id):
        if field_value(field_name, inputs) is None:
            return False
    return True


def dfs_collect_respecting_node_gates(
    store: GraphStore,
    start_id: str,
    *,
    inputs: dict[str, Fact],
    skipped_nodes: list[dict[str, Any]] | None = None,
) -> tuple[list[str], list[GraphEdgeRecord]]:
    """DFS collect that stops descending when node expansion assumptions are unsatisfied."""

    def _expansion_gate(node_id: str) -> bool:
        if node_allows_child_traversal(store, node_id, inputs):
            return True
        if skipped_nodes is not None:
            record_expansion_skip(
                skipped_nodes,
                node_id,
                expansion_gate_evaluation(store, node_id, inputs),
            )
        return False

    return dfs_collect(store, start_id, inputs=inputs, expansion_gate=_expansion_gate)
