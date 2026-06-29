"""Lazy graph expansion for step-by-step workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.graph_store import GraphStore
from engine.graph.node_behaviors import is_data_parameter
from engine.graph.param_priority import parameter_collection_priority
from engine.graph.traversal import dfs_collect, topological_order
from engine.reference.graph_db import GraphEdgeRecord
from engine.reference.node_types import (
    expansion_priority_order,
    is_ui_parameter,
    parameter_input_id,
)
from models.input import EngineeringInput


@dataclass
class ExpansionState:
    root_id: str
    active_nodes: list[str] = field(default_factory=list)
    edges: list[GraphEdgeRecord] = field(default_factory=list)
    skipped_nodes: list[dict[str, Any]] = field(default_factory=list)
    pending_fields: list[str] = field(default_factory=list)


def _priority_key(store: GraphStore, node_id: str, active_nodes: set[str]) -> tuple[Any, ...]:
    meta = store.metadata(node_id)
    node_type = store.node_type(node_id) or ""
    if is_data_parameter(meta, node_type):
        priority_num = parameter_collection_priority(store, node_id, active_nodes)
    else:
        priority = meta.get("priority", 100)
        try:
            priority_num = int(priority)
        except (TypeError, ValueError):
            priority_num = 100
    type_order = expansion_priority_order(node_type, meta)
    return (type_order, priority_num, node_id)


def _collect_expansion_assumptions(
    store: GraphStore,
    root_id: str,
) -> list[str]:
    """Assumption and interaction nodes directly linked from workflow root."""
    fields: list[str] = []
    for edge in store.outgoing(root_id):
        if edge.edge_type not in {"contains", "anchors_to"}:
            continue
        node = store.get_node(edge.to_id)
        if node is None:
            continue
        if is_ui_parameter(node.metadata, node.node_type):
            field_name = parameter_input_id(node.metadata)
            if field_name:
                fields.append(field_name)
    anchored = store.metadata(root_id).get("anchors_to")
    if isinstance(anchored, str):
        for edge in store.outgoing(anchored, edge_types={"contains"}):
            node = store.get_node(edge.to_id)
            if node and is_ui_parameter(node.metadata, node.node_type):
                field_name = parameter_input_id(node.metadata)
                if field_name:
                    fields.append(field_name)
    return fields


def expansion_gate_ready(
    store: GraphStore,
    root_id: str,
    inputs: dict[str, EngineeringInput],
) -> bool:
    for field_name in _collect_expansion_assumptions(store, root_id):
        if field_value(field_name, inputs) is None:
            return False
    return True


def expand_workflow(
    store: GraphStore,
    root_id: str,
    inputs: dict[str, EngineeringInput],
    *,
    lazy: bool = False,
) -> ExpansionState:
    """Expand workflow graph. When lazy=True, only expand when gate inputs are ready."""
    state = ExpansionState(root_id=root_id)
    root = store.get_node(root_id)
    if root is None:
        return state

    if lazy and not expansion_gate_ready(store, root_id, inputs):
        state.active_nodes = [root_id]
        anchors = root.metadata.get("anchors_to")
        if isinstance(anchors, str):
            state.active_nodes.append(anchors)
        for field_name in _collect_expansion_assumptions(store, root_id):
            if field_value(field_name, inputs) is None:
                state.pending_fields.append(field_name)
        return state

    order, edges = dfs_collect(store, root_id, inputs=inputs)
    node_set = set(order)
    for edge in edges:
        if edge.to_id not in node_set:
            node_set.add(edge.to_id)
            order.append(edge.to_id)

    anchors = root.metadata.get("anchors_to")
    if isinstance(anchors, str) and anchors not in node_set:
        anchor_order, anchor_edges = dfs_collect(store, anchors, inputs=inputs)
        for node_id in anchor_order:
            if node_id not in node_set:
                node_set.add(node_id)
                order.append(node_id)
        edges.extend(anchor_edges)

    sorted_order = list(
        topological_order(
            node_set,
            edges,
            priority_key=lambda node_id: _priority_key(store, node_id, node_set),
        )
    )
    state.active_nodes = sorted_order
    state.edges = edges
    return state


def next_pending_parameter(
    store: GraphStore,
    expansion: ExpansionState,
    inputs: dict[str, EngineeringInput],
) -> str | None:
    """Return the next unresolved parameter input_id on the active path."""
    for node_id in expansion.active_nodes:
        node = store.get_node(node_id)
        if node is None or node.node_type != "parameter":
            continue
        if is_ui_parameter(node.metadata, node.node_type):
            continue
        input_id = parameter_input_id(node.metadata)
        if not input_id:
            continue
        if field_value(input_id, inputs) is None:
            resolution = node.metadata.get("resolution") or {}
            if isinstance(resolution, dict):
                method = str(resolution.get("method", "user_input"))
                if method == "node_output":
                    continue
            return input_id
    return None
