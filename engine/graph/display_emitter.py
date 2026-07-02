"""Emit display output blocks from micro-graph nodes."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.doc_templates import build_doc_context
from engine.graph.graph_store import GraphStore
from engine.graph.lazy_expander import ExpansionState
from engine.graph.node_behaviors import (
    is_reference_designation,
    is_reference_quantity,
)
from engine.reference.graph_edge_schema import workflow_anchor_target
from engine.reference.relationship_taxonomy import CONTAINS_TRAVERSAL_TYPES, PARAMETER_CONCEPT_TRAVERSAL_TYPES
from models.fact import Fact


def _referenced_concept(store: GraphStore, node_id: str) -> dict[str, str]:
    """Dimension or designation symbol from parameter → quantity/designation links."""
    concept: dict[str, str] = {}
    for edge in store.outgoing(node_id, edge_types=PARAMETER_CONCEPT_TRAVERSAL_TYPES | {"has_dimension"}):
        ref_meta = store.metadata(edge.to_id)
        ref_type = store.node_type(edge.to_id) or ""
        if is_reference_quantity(ref_meta, ref_type):
            dimension = str(ref_meta.get("dimension", "")).strip()
            if dimension:
                concept["dimension"] = dimension
        elif is_reference_designation(ref_meta, ref_type):
            symbol = str(ref_meta.get("symbol", "")).strip()
            if symbol:
                concept["designation_symbol"] = symbol
    return concept


def _parameter_table_row(
    store: GraphStore,
    node_id: str,
    inputs: dict[str, Fact],
    edge_meta: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    meta = store.metadata(node_id)
    node_type = store.node_type(node_id) or ""
    if is_reference_quantity(meta, node_type) or is_reference_designation(meta, node_type):
        return None
    input_id = str(meta.get("input_id", ""))
    value = field_value(input_id, inputs) if input_id else None
    row: dict[str, Any] = {
        "symbol": str(meta.get("symbol", "")),
        "name": str(meta.get("title") or meta.get("symbol", "")),
        "description": str(meta.get("description", "")),
        "unit": str(meta.get("unit", "")),
        "value": value,
        "node_id": node_id,
        "input_id": input_id,
    }
    row.update(_referenced_concept(store, node_id))
    if edge_meta:
        if edge_meta.get("alias"):
            row["symbol"] = str(edge_meta["alias"])
        if edge_meta.get("displayName"):
            row["name"] = str(edge_meta["displayName"])
        if edge_meta.get("role"):
            row["role"] = str(edge_meta["role"])
    return row


def _text_block(node_id: str, role: str, body: str, title: str | None = None) -> dict[str, Any]:
    return {
        "type": "paragraph",
        "node_id": node_id,
        "role": role,
        "title": title,
        "text": body.strip(),
    }


def _resolve_node_documentation(store, node_id, *, context):
    from engine.graph.documentation_resolver import resolve_node_documentation

    return resolve_node_documentation(store, node_id, context=context)


def _doc_text(doc, *fields: str, fallback: str = "") -> str:
    for field in fields:
        value = getattr(doc, field, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback.strip()


def emit_initiation_blocks(
    store: GraphStore,
    root_id: str,
    *,
    inputs: dict[str, Fact] | None = None,
) -> list[dict[str, Any]]:
    """Text blocks shown when a workflow opens."""
    blocks: list[dict[str, Any]] = []
    root = store.get_node(root_id)
    if root is None:
        return blocks

    context = build_doc_context(None, inputs=inputs or {})
    root_doc = _resolve_node_documentation(store, root_id, context=context)
    initiation_text = _doc_text(root_doc, "summary", "description", "before_enter")
    if not initiation_text:
        initiation_text = str(root.metadata.get("purpose", "")).strip()
    if initiation_text:
        title = _doc_text(root_doc, "title") or str(root.metadata.get("title", ""))
        blocks.append(_text_block(root_id, "initiation", initiation_text, title or None))

    for edge in store.outgoing(root_id, edge_types=CONTAINS_TRAVERSAL_TYPES):
        node = store.get_node(edge.to_id)
        if node and node.node_type == "text" and node.metadata.get("role") == "initiation":
            node_doc = _resolve_node_documentation(store, node.node_id, context=context)
            body = _doc_text(node_doc, "description", "summary")
            if not body:
                body = node.body or str(node.metadata.get("text", ""))
            blocks.append(
                _text_block(
                    node.node_id,
                    "initiation",
                    body,
                    _doc_text(node_doc, "title") or str(node.metadata.get("title", "")) or None,
                )
            )

    anchors = workflow_anchor_target(root.metadata)
    if isinstance(anchors, str):
        for edge in store.outgoing(anchors, edge_types=CONTAINS_TRAVERSAL_TYPES):
            node = store.get_node(edge.to_id)
            if node and node.node_type == "text" and node.metadata.get("role") == "initiation":
                node_doc = _resolve_node_documentation(store, node.node_id, context=context)
                body = _doc_text(node_doc, "description", "summary")
                if not body:
                    body = node.body or str(node.metadata.get("text", ""))
                blocks.append(
                    _text_block(
                        node.node_id,
                        "initiation",
                        body,
                        _doc_text(node_doc, "title") or str(node.metadata.get("title", "")) or None,
                    )
                )
    return blocks


def emit_equation_blocks(
    store: GraphStore,
    equation_id: str,
    inputs: dict[str, Fact],
    *,
    result: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Ordered blocks for equation intro, symbol table, substitution, and result."""
    blocks: list[dict[str, Any]] = []
    eq_meta = store.metadata(equation_id)
    display = str(eq_meta.get("display_latex") or eq_meta.get("sympy", ""))

    context = build_doc_context(None, inputs=inputs)
    for edge in store.outgoing(equation_id, edge_types={"explains"}):
        node = store.get_node(edge.to_id)
        if node and node.node_type == "text":
            role = str(node.metadata.get("role", ""))
            if role == "equation_intro":
                node_doc = _resolve_node_documentation(store, node.node_id, context=context)
                body = _doc_text(node_doc, "description", "instructions", "summary")
                if not body:
                    body = node.body or str(node.metadata.get("text", ""))
                blocks.append(
                    _text_block(
                        node.node_id,
                        "equation_intro",
                        body,
                    )
                )

    rows: list[dict[str, Any]] = []
    for item in eq_meta.get("requires") or []:
        binding = resolve_require_binding(store, item)
        if binding is None:
            continue
        row = _parameter_table_row(store, binding.param_id, inputs, binding.metadata)
        if row is not None:
            rows.append(row)
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
        equation_block: dict[str, Any] = {
            "type": "equation_result",
            "node_id": equation_id,
            "equation": display,
            "substitution": result.get("substitution"),
            "result": result.get("result"),
            "outputs": result.get("outputs", {}),
        }
        render_steps = result.get("render_steps")
        if isinstance(render_steps, dict) and render_steps:
            equation_block["steps"] = render_steps
        blocks.append(equation_block)
        for edge in store.outgoing(equation_id, edge_types={"explains"}):
            node = store.get_node(edge.to_id)
            if node and node.node_type == "text" and node.metadata.get("role") == "result_explanation":
                node_doc = _resolve_node_documentation(store, node.node_id, context=context)
                body = _doc_text(node_doc, "description", "summary", "after_exit")
                if not body:
                    body = node.body or str(node.metadata.get("text", ""))
                blocks.append(
                    _text_block(
                        node.node_id,
                        "result_explanation",
                        body,
                    )
                )
    return blocks


def emit_active_context(
    store: GraphStore,
    expansion: ExpansionState,
    inputs: dict[str, Fact],
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
