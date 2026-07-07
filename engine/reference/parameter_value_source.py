"""Resolve standards-node references for parameter values not yet available in task state."""

from __future__ import annotations

import re
from typing import Any

from engine.graph.lazy_expander import _node_active_on_path
from engine.graph.lookup_parameter_resolution import lookup_resolution_for_parameter, parameter_resolution_for_parameter
from engine.reference.paragraph_hierarchy import paragraph_reference
from engine.reference.standards_reader import StandardsReader
from models.task import Task


def resolve_parameter_value_reference(
    reader: StandardsReader,
    param_id: str,
    task: Task,
    *,
    active_nodes: set[str] | frozenset[str] | None = None,
) -> dict[str, str] | None:
    """Return a paragraph/table link when a parameter is produced by graph nodes, not user input."""
    param_id = str(param_id or "").strip()
    if not param_id:
        return None

    store = reader.graph_store
    if not store.available:
        return None

    try:
        param = reader.load(param_id)
    except FileNotFoundError:
        return None

    meta = param.metadata
    if _is_user_input_parameter(store, param_id, meta):
        return None

    inputs = task.fact_store.active_facts()
    active = set(active_nodes) if active_nodes is not None else set(task.active_nodes or [])
    producers = _active_producers_for_parameter(store, param_id, inputs)
    if not producers:
        return None

    selected = _select_producer(producers, active)
    return _reference_link_from_producer(reader, selected)


def resolve_input_value_reference(
    reader: StandardsReader,
    input_id: str,
    task: Task,
    *,
    param_id: str | None = None,
    active_nodes: set[str] | frozenset[str] | None = None,
) -> dict[str, str] | None:
    """Resolve a value reference from a runtime input key or explicit PARAM id."""
    resolved_param = str(param_id or "").strip()
    if not resolved_param and input_id:
        resolved_param = _param_id_for_input_key(reader, str(input_id).strip())
    if not resolved_param:
        return None
    return resolve_parameter_value_reference(
        reader,
        resolved_param,
        task,
        active_nodes=active_nodes,
    )


def _param_id_for_input_key(reader: StandardsReader, input_id: str) -> str:
    from engine.reference.parameter_keys import param_node_id_for_input

    candidate = param_node_id_for_input(input_id)
    if reader.graph_store.available and reader.graph_store.get_node(candidate) is not None:
        return candidate

    store = reader.graph_store
    if not store.available:
        return candidate

    for node in store.list_nodes(node_type="parameter"):
        key = str(node.metadata.get("key") or node.metadata.get("input_id") or "").strip()
        if key == input_id:
            return node.node_id
        for alias in node.metadata.get("aliases") or []:
            if str(alias).strip().lower() == input_id.replace("_", " ").lower():
                return node.node_id
    return candidate


def _is_user_input_parameter(
    store,
    param_id: str,
    meta: dict[str, Any],
) -> bool:
    parameter_class = str(meta.get("parameter_class", "")).strip()
    if parameter_class == "calculated_quantity":
        return False
    if store.incoming(param_id, edge_types={"calculates_parameter", "returns_parameter"}):
        return False

    resolution = meta.get("resolution") or parameter_resolution_for_parameter(store, param_id) or {}
    method = str(resolution.get("method", "user_input")) if isinstance(resolution, dict) else "user_input"
    return method == "user_input"

def _active_producers_for_parameter(store, param_id: str, inputs: dict[str, Any]) -> list[str]:
    producers: list[str] = []
    for edge_type in ("calculates_parameter", "returns_parameter"):
        for edge in store.incoming(param_id, edge_types={edge_type}):
            producer_id = edge.from_id
            if not _node_active_on_path(store, producer_id, inputs):
                continue
            if producer_id not in producers:
                producers.append(producer_id)
    return producers


def _select_producer(producers: list[str], active_nodes: set[str]) -> str:
    for producer_id in producers:
        if producer_id in active_nodes:
            return producer_id
    return producers[0]


def _reference_link_from_producer(
    reader: StandardsReader,
    producer_id: str,
) -> dict[str, str] | None:
    try:
        record = reader.load(producer_id)
    except FileNotFoundError:
        return None

    meta = record.metadata
    node_type = str(meta.get("type", ""))

    if node_type == "equation":
        authority = meta.get("authority") or {}
        authorized = authority.get("authorized_by") or []
        if authorized:
            ref_node_id = str(authorized[0]).strip()
            if ref_node_id:
                return _paragraph_reference_link(reader, ref_node_id)
        paragraph_number = str(meta.get("paragraph_number") or "").strip()
        if paragraph_number:
            return _paragraph_reference_link(reader, paragraph_number)

    if node_type == "lookup":
        table_ref = _lookup_table_reference(reader, meta)
        if table_ref is not None:
            return table_ref

    return _paragraph_reference_link(reader, producer_id)


def _lookup_table_api_id(
    reader: StandardsReader,
    lookup_meta: dict[str, Any],
    table_ref: str,
) -> str:
    """Return a table id accepted by standards table APIs."""
    source = lookup_meta.get("source")
    if isinstance(source, dict):
        db_table_id = str(source.get("table_id") or "").strip()
        if db_table_id and reader.tables_database.resolve_table_id(db_table_id):
            return db_table_id

    tables_db = reader.tables_database
    for candidate in (table_ref, str(lookup_meta.get("id") or "").strip()):
        if candidate:
            resolved = tables_db.resolve_table_id(candidate)
            if resolved:
                return resolved
    return table_ref or str(lookup_meta.get("id") or "").strip()


def _lookup_table_reference(
    reader: StandardsReader,
    lookup_meta: dict[str, Any],
) -> dict[str, str] | None:
    from engine.reference.table_metadata import table_citation_labels

    lookup_cfg = lookup_meta.get("lookup")
    table_ref = ""
    if isinstance(lookup_cfg, dict):
        table_ref = str(lookup_cfg.get("table") or lookup_cfg.get("table_id") or "").strip()
    if not table_ref:
        for item in lookup_meta.get("lookups") or []:
            if isinstance(item, dict):
                table_ref = str(item.get("table_id") or item.get("table") or "").strip()
                if table_ref:
                    break

    table_number, paragraph_number = table_citation_labels(reader, table_ref) if table_ref else ("", "")
    if table_number:
        label = f"Table {table_number}"
        table_id = _lookup_table_api_id(reader, lookup_meta, table_ref)
        if table_id:
            return {
                "node_id": table_id,
                "label": label,
                "paragraph": paragraph_number or None,
                "reference_kind": "table",
            }
    return _paragraph_reference_link(reader, str(lookup_meta.get("id") or ""))


def _paragraph_reference_link(reader: StandardsReader, node_id: str) -> dict[str, str] | None:
    node_id = str(node_id or "").strip()
    if not node_id:
        return None

    try:
        record = reader.load(node_id)
        paragraph = paragraph_reference(record.metadata) or node_id
    except FileNotFoundError:
        paragraph = node_id

    display_para = _display_paragraph_number(paragraph)
    label = f"§{display_para}" if display_para else node_id
    return {
        "node_id": node_id,
        "label": label,
        "paragraph": paragraph or None,
    }


def _display_paragraph_number(paragraph: str) -> str:
    text = str(paragraph or "").strip()
    if not text:
        return ""
    if re.search(r"-[a-z]$", text):
        return re.sub(r"-[a-z]$", "", text)
    return text
