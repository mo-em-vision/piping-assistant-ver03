"""Emit display output blocks from micro-graph nodes."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.graph_store import GraphStore
from engine.graph.lazy_expander import ExpansionState
from models.input import EngineeringInput


def _text_block(node_id: str, role: str, body: str, title: str | None = None) -> dict[str, Any]:
    return {
        "type": "paragraph",
        "node_id": node_id,
        "role": role,
        "title": title,
        "text": body.strip(),
    }


def _parameter_table_row(store: GraphStore, node_id: str, inputs: dict[str, EngineeringInput]) -> dict[str, Any]:
    meta = store.metadata(node_id)
    input_id = str(meta.get("input_id", ""))
    value = field_value(input_id, inputs) if input_id else None
    return {
        "symbol": str(meta.get("symbol", "")),
        "name": str(meta.get("title") or meta.get("symbol", "")),
        "description": str(meta.get("description", "")),
        "unit": str(meta.get("unit", "")),
        "value": value,
        "node_id": node_id,
        "input_id": input_id,
    }


def emit_initiation_blocks(store: GraphStore, root_id: str) -> list[dict[str, Any]]:
    """Text blocks shown when a workflow opens."""
    blocks: list[dict[str, Any]] = []
    root = store.get_node(root_id)
    if root is None:
        return blocks

    purpose = str(root.metadata.get("purpose", "")).strip()
    if purpose:
        blocks.append(_text_block(root_id, "initiation", purpose, str(root.metadata.get("title", ""))))

    for edge in store.outgoing(root_id, edge_types={"contains"}):
        node = store.get_node(edge.to_id)
        if node and node.node_type == "text" and node.metadata.get("role") == "initiation":
            blocks.append(
                _text_block(
                    node.node_id,
                    "initiation",
                    node.body or str(node.metadata.get("text", "")),
                    str(node.metadata.get("title", "")),
                )
            )

    anchors = root.metadata.get("anchors_to")
    if isinstance(anchors, str):
        for edge in store.outgoing(anchors, edge_types={"contains"}):
            node = store.get_node(edge.to_id)
            if node and node.node_type == "text" and node.metadata.get("role") == "initiation":
                blocks.append(
                    _text_block(
                        node.node_id,
                        "initiation",
                        node.body or str(node.metadata.get("text", "")),
                        str(node.metadata.get("title", "")),
                    )
                )
    return blocks


def emit_equation_blocks(
    store: GraphStore,
    equation_id: str,
    inputs: dict[str, EngineeringInput],
    *,
    result: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Ordered blocks for equation intro, symbol table, substitution, and result."""
    blocks: list[dict[str, Any]] = []
    eq_meta = store.metadata(equation_id)
    display = str(eq_meta.get("display_latex") or eq_meta.get("sympy", ""))

    for edge in store.outgoing(equation_id, edge_types={"explains"}):
        node = store.get_node(edge.to_id)
        if node and node.node_type == "text":
            role = str(node.metadata.get("role", ""))
            if role == "equation_intro":
                blocks.append(
                    _text_block(
                        node.node_id,
                        "equation_intro",
                        node.body or str(node.metadata.get("text", "")),
                    )
                )

    rows: list[dict[str, Any]] = []
    for edge in store.outgoing(equation_id, edge_types={"requires"}):
        rows.append(_parameter_table_row(store, edge.to_id, inputs))
    if rows:
        blocks.append(
            {
                "type": "symbol_table",
                "node_id": equation_id,
                "equation": display,
                "rows": rows,
            }
        )

    if result:
        blocks.append(
            {
                "type": "equation_result",
                "node_id": equation_id,
                "equation": display,
                "substitution": result.get("substitution"),
                "result": result.get("result"),
                "outputs": result.get("outputs", {}),
            }
        )
        for edge in store.outgoing(equation_id, edge_types={"explains"}):
            node = store.get_node(edge.to_id)
            if node and node.node_type == "text" and node.metadata.get("role") == "result_explanation":
                blocks.append(
                    _text_block(
                        node.node_id,
                        "result_explanation",
                        node.body or str(node.metadata.get("text", "")),
                    )
                )
    return blocks


def emit_active_context(
    store: GraphStore,
    expansion: ExpansionState,
    inputs: dict[str, EngineeringInput],
    *,
    focus_node_id: str | None = None,
) -> list[dict[str, Any]]:
    """Build display blocks for the current workflow step."""
    blocks: list[dict[str, Any]] = []
    target = focus_node_id
    if target is None:
        for node_id in expansion.active_nodes:
            node = store.get_node(node_id)
            if node and node.node_type == "equation":
                target = node_id
                break
    if target and store.node_type(target) == "equation":
        blocks.extend(emit_equation_blocks(store, target, inputs))
    return blocks
