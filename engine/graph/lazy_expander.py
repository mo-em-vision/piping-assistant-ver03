"""Lazy graph expansion for step-by-step workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.conditions import when_clause_matches
from engine.graph.expansion_policy import (
    collect_workflow_expansion_fields,
    dfs_collect_respecting_node_gates,
    node_allows_child_traversal,
    workflow_expansion_gate_ready,
)
from engine.graph.assumption_checker import applicability_expansion_status
from engine.graph.graph_store import GraphStore
from engine.graph.node_behaviors import (
    is_data_parameter,
    is_reference_designation,
    is_reference_quantity,
)
from engine.graph.lookup_parameter_resolution import parameter_resolution_for_parameter
from engine.graph.param_priority import parameter_collection_priority
from engine.graph.traversal import dfs_collect, topological_order
from engine.reference.graph_db import GraphEdgeRecord
from engine.reference.graph_edge_schema import workflow_anchor_target
from engine.reference.relationship_taxonomy import DEPENDENCY_TRAVERSAL_TYPES
from engine.reference.node_types import (
    expansion_priority_order,
    is_ui_parameter,
    parameter_input_id,
)
from models.fact import Fact


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
    """Backward-compatible alias for workflow expansion gate fields."""
    return collect_workflow_expansion_fields(store, root_id)


def expansion_gate_ready(
    store: GraphStore,
    root_id: str,
    inputs: dict[str, Fact],
) -> bool:
    return workflow_expansion_gate_ready(store, root_id, inputs)


def _should_skip_expansion_edge(
    store: GraphStore,
    node_id: str,
    edge: GraphEdgeRecord,
) -> bool:
    """Skip provenance edges that must not widen workflow execution subgraphs."""
    edge_type = edge.edge_type
    node_type = store.node_type(node_id) or ""
    if node_type == "parameter" and edge_type in {"uses", "used_by"}:
        # Parameter used_by lists historical consumers; path selection uses producers/requires.
        return True
    if node_type in {"equation", "validation_rule"} and edge_type == "authorized_by":
        # Citation anchors are not execution routing; paragraphs/workflows own path edges.
        return True
    return False


def _expand_metadata_dependencies(
    store: GraphStore,
    node_set: set[str],
    order: list[str],
    edges: list[GraphEdgeRecord],
    inputs: dict[str, Fact],
    skipped_nodes: list[dict[str, Any]],
) -> None:
    """Include conditional dependency targets from stored ``edges`` on active nodes."""
    queue = list(order)
    while queue:
        node_id = queue.pop(0)
        if not node_allows_child_traversal(store, node_id, inputs):
            continue
        for edge in store.outgoing(
            node_id,
            edge_types=DEPENDENCY_TRAVERSAL_TYPES,
        ):
            if _should_skip_expansion_edge(store, node_id, edge):
                continue
            dep_id = edge.to_id
            when = edge.metadata.get("when") if edge.metadata else None
            if when and isinstance(when, dict) and not when_clause_matches(when, inputs):
                reason = "conditional dependency not active"
                pending = False
                field_name = str(when.get("field", ""))
                if field_name and field_value(field_name, inputs) is None:
                    pending = True
                    reason = f"when {field_name} in {when.get('in')} not satisfied (field missing)"
                else:
                    reason = f"when {when.get('field')} in {when.get('in')} not satisfied"
                skipped_nodes.append(
                    {
                        "node_id": dep_id,
                        "reason": reason,
                        "field": field_name,
                        "pending": pending,
                    }
                )
                continue

            if dep_id in node_set:
                continue
            dep_order, dep_edges = dfs_collect_respecting_node_gates(
                store,
                dep_id,
                inputs=inputs,
                skipped_nodes=skipped_nodes,
            )
            for dep_node_id in dep_order:
                if dep_node_id not in node_set:
                    node_set.add(dep_node_id)
                    order.append(dep_node_id)
                    queue.append(dep_node_id)
            for dep_edge in dep_edges:
                edges.append(dep_edge)
                if dep_edge.to_id not in node_set:
                    node_set.add(dep_edge.to_id)
                    order.append(dep_edge.to_id)
                    queue.append(dep_edge.to_id)
            node_set.add(dep_id)
            if dep_id not in order:
                order.append(dep_id)
            queue.append(dep_id)


def _node_active_on_path(
    store: GraphStore,
    node_id: str,
    inputs: dict[str, Fact],
) -> bool:
    """Return False when authored applicability rules rule this node out or are undecided."""
    node = store.get_node(node_id)
    if node is None:
        return True
    return applicability_expansion_status(node.metadata, inputs) == "satisfied"


def _expand_output_producers(
    store: GraphStore,
    node_set: set[str],
    order: list[str],
    edges: list[GraphEdgeRecord],
    inputs: dict[str, Fact],
) -> None:
    """Include lookup/equation nodes that populate required parameter outputs."""
    queue = [node_id for node_id in order if store.node_type(node_id) == "parameter"]
    while queue:
        param_id = queue.pop(0)
        for edge in store.incoming(
            param_id,
            edge_types={"implements", "parameter", "outputs", "returns_parameter"},
        ):
            producer_id = edge.from_id
            if producer_id in node_set:
                continue
            if not node_allows_child_traversal(store, producer_id, inputs):
                continue
            producer_type = store.node_type(producer_id)
            if producer_type == "lookup":
                producer_node = store.get_node(producer_id)
                if producer_node is None:
                    continue
                if applicability_expansion_status(producer_node.metadata, inputs) != "satisfied":
                    continue
            elif not _node_active_on_path(store, producer_id, inputs):
                continue
            producer_order, producer_edges = dfs_collect_respecting_node_gates(
                store,
                producer_id,
                inputs=inputs,
            )
            for producer_node_id in producer_order:
                if not _node_active_on_path(store, producer_node_id, inputs):
                    continue
                if producer_node_id not in node_set:
                    node_set.add(producer_node_id)
                    order.append(producer_node_id)
                    if store.node_type(producer_node_id) == "parameter":
                        queue.append(producer_node_id)
            for producer_edge in producer_edges:
                edges.append(producer_edge)
                if producer_edge.to_id not in node_set:
                    node_set.add(producer_edge.to_id)
                    order.append(producer_edge.to_id)
                    if store.node_type(producer_edge.to_id) == "parameter":
                        queue.append(producer_edge.to_id)
            node_set.add(producer_id)
            if producer_id not in order:
                order.append(producer_id)
            edges.append(edge)
            if store.node_type(producer_id) == "parameter":
                queue.append(producer_id)


def _ordering_edges(
    store: GraphStore,
    edges: list[GraphEdgeRecord],
) -> list[GraphEdgeRecord]:
    """Normalize edges for execution ordering (dependencies before dependents)."""
    ordered: list[GraphEdgeRecord] = []
    for edge in edges:
        if edge.edge_type == "requires" and store.node_type(edge.from_id) == "calculation":
            ordered.append(
                GraphEdgeRecord(
                    from_id=edge.to_id,
                    to_id=edge.from_id,
                    edge_type=edge.edge_type,
                    metadata=edge.metadata,
                )
            )
            continue
        if edge.edge_type == "constrains_equation":
            # Validation rules depend on equation outputs — run equations first.
            ordered.append(
                GraphEdgeRecord(
                    from_id=edge.to_id,
                    to_id=edge.from_id,
                    edge_type="requires",
                    metadata=edge.metadata,
                )
            )
            continue
        ordered.append(edge)
    return ordered


def _expand_parameter_anchor_paragraphs(
    store: GraphStore,
    anchor_id: str,
    *,
    node_set: set[str],
    order: list[str],
    edges: list[GraphEdgeRecord],
    inputs: dict[str, Fact],
    skipped_nodes: list[dict[str, Any]],
) -> None:
    """When the definition anchor is a parameter, traverse graph context that defines it."""
    if store.node_type(anchor_id) != "parameter":
        return

    def _merge_subgraph(start_id: str) -> None:
        sub_order, sub_edges = dfs_collect_respecting_node_gates(
            store,
            start_id,
            inputs=inputs,
            skipped_nodes=skipped_nodes,
        )
        for node_id in sub_order:
            if node_id not in node_set:
                node_set.add(node_id)
                order.append(node_id)
        edges.extend(sub_edges)

    for intro_edge in store.incoming(anchor_id, edge_types={"introduces_parameter"}):
        paragraph_id = intro_edge.from_id
        if store.node_type(paragraph_id) == "paragraph":
            _merge_subgraph(paragraph_id)

    for producer_edge in store.incoming(anchor_id, edge_types={"calculates_parameter"}):
        producer_id = producer_edge.from_id
        if store.node_type(producer_id) in {"equation", "lookup", "calculation"}:
            _merge_subgraph(producer_id)


def _expand_equation_producer_ordering(
    store: GraphStore,
    node_set: set[str],
    edges: list[GraphEdgeRecord],
) -> None:
    """Ensure equations that consume calculated parameters run after their producers."""
    for node_id in list(node_set):
        if store.node_type(node_id) != "equation":
            continue
        for req_edge in store.outgoing(node_id, edge_types={"requires_parameter", "requires"}):
            param_id = req_edge.to_id
            if store.node_type(param_id) != "parameter":
                continue
            for prod_edge in store.incoming(
                param_id,
                edge_types={"calculates_parameter", "implements", "calculates"},
            ):
                producer_id = prod_edge.from_id
                if producer_id not in node_set or producer_id == node_id:
                    continue
                if store.node_type(producer_id) != "equation":
                    continue
                edges.append(
                    GraphEdgeRecord(
                        from_id=producer_id,
                        to_id=node_id,
                        edge_type="requires",
                        metadata={
                            "reason": (
                                f"{node_id} requires output from {producer_id} "
                                f"via {param_id}"
                            )
                        },
                    )
                )


def expand_workflow(
    store: GraphStore,
    root_id: str,
    inputs: dict[str, Fact],
    *,
    lazy: bool = False,
) -> ExpansionState:
    """Expand workflow graph. When lazy=True, only expand when gate inputs are ready."""
    resolved_root = store.resolve_node_id(root_id) or root_id
    state = ExpansionState(root_id=resolved_root)
    root = store.get_node(resolved_root)
    if root is None:
        return state

    if lazy and not expansion_gate_ready(store, resolved_root, inputs):
        state.active_nodes = [resolved_root]
        anchors = workflow_anchor_target(root.metadata)
        if isinstance(anchors, str):
            _expand_parameter_anchor_paragraphs(
                store,
                anchors,
                node_set=set(state.active_nodes),
                order=state.active_nodes,
                edges=[],
                inputs=inputs,
                skipped_nodes=state.skipped_nodes,
            )
            if anchors not in state.active_nodes:
                anchor_order, _ = dfs_collect_respecting_node_gates(
                    store,
                    anchors,
                    inputs=inputs,
                    skipped_nodes=state.skipped_nodes,
                )
                for node_id in anchor_order:
                    if node_id not in state.active_nodes:
                        state.active_nodes.append(node_id)
        for field_name in _collect_expansion_assumptions(store, resolved_root):
            if field_value(field_name, inputs) is None:
                state.pending_fields.append(field_name)
        return state

    order, edges = dfs_collect_respecting_node_gates(
        store,
        resolved_root,
        inputs=inputs,
        skipped_nodes=state.skipped_nodes,
    )
    node_set = set(order)
    for edge in edges:
        if edge.to_id not in node_set:
            node_set.add(edge.to_id)
            order.append(edge.to_id)

    anchors = workflow_anchor_target(root.metadata)
    if isinstance(anchors, str):
        _expand_parameter_anchor_paragraphs(
            store,
            anchors,
            node_set=node_set,
            order=order,
            edges=edges,
            inputs=inputs,
            skipped_nodes=state.skipped_nodes,
        )
        if anchors not in node_set:
            anchor_order, anchor_edges = dfs_collect_respecting_node_gates(
                store,
                anchors,
                inputs=inputs,
                skipped_nodes=state.skipped_nodes,
            )
            for node_id in anchor_order:
                if node_id not in node_set:
                    node_set.add(node_id)
                    order.append(node_id)
            edges.extend(anchor_edges)

    _expand_metadata_dependencies(store, node_set, order, edges, inputs, state.skipped_nodes)
    _expand_output_producers(store, node_set, order, edges, inputs)
    _expand_equation_producer_ordering(store, node_set, edges)

    for calc_id in list(node_set):
        if store.node_type(calc_id) != "calculation":
            continue
        for req_edge in store.outgoing(calc_id, edge_types={"requires", "requires_parameter"}):
            param_id = req_edge.to_id
            for prod_edge in store.incoming(param_id, edge_types={"implements", "parameter"}):
                producer_id = prod_edge.from_id
                if producer_id not in node_set:
                    continue
                edges.append(
                    GraphEdgeRecord(
                        from_id=producer_id,
                        to_id=calc_id,
                        edge_type="requires",
                        metadata={"reason": f"{calc_id} consumes output from {producer_id}"},
                    )
                )

    sorted_order = list(
        topological_order(
            node_set,
            _ordering_edges(store, edges),
            priority_key=lambda node_id: _priority_key(store, node_id, node_set),
        )
    )
    state.active_nodes = [
        node_id for node_id in sorted_order if _node_active_on_path(store, node_id, inputs)
    ]
    state.edges = edges
    return state


def next_pending_parameter(
    store: GraphStore,
    expansion: ExpansionState,
    inputs: dict[str, Fact],
) -> str | None:
    """Return the next unresolved parameter input_id on the active path."""
    for node_id in expansion.active_nodes:
        node = store.get_node(node_id)
        if node is None:
            continue
        if is_reference_quantity(node.metadata, node.node_type) or is_reference_designation(
            node.metadata, node.node_type
        ):
            continue
        if node.node_type != "parameter":
            continue
        if is_ui_parameter(node.metadata, node.node_type):
            continue
        input_id = parameter_input_id(node.metadata)
        if not input_id:
            continue
        if field_value(input_id, inputs) is None:
            resolution = parameter_resolution_for_parameter(store, node_id) or {}
            if isinstance(resolution, dict):
                method = str(resolution.get("method", "user_input"))
                if method in {"node_output", "table_lookup", "material_catalog"}:
                    continue
            return input_id
    return None
