"""Resolve standards-node references for parameter values not yet available in task state."""

from __future__ import annotations

import re
from typing import Any

from engine.graph.lazy_expander import _node_active_on_path
from engine.graph.lookup_parameter_resolution import lookup_resolution_for_parameter, parameter_resolution_for_parameter
from engine.reference.paragraph_hierarchy import paragraph_reference
from engine.reference.standards_reader import StandardsReader
from models.task import Task

AWAITING_USER_INPUT = "Awaiting user input"

_VALUE_PROVENANCE_SOURCE_TYPES = frozenset(
    {"user_input", "equation_output", "table_lookup", "default", "unknown"}
)
_VALUE_PROVENANCE_STATUSES = frozenset(
    {"resolved", "pending_derived", "awaiting_user_input"}
)


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


def build_value_provenance(
    reader: StandardsReader,
    param_id: str,
    task: Task,
    *,
    display_value: str | None = None,
    active_nodes: set[str] | frozenset[str] | None = None,
    trace_source_type: str | None = None,
    trace_source_ref: str | None = None,
) -> dict[str, Any]:
    """Build canonical single-hop value provenance for equation input table rows."""
    param_id = str(param_id or "").strip()
    display = str(display_value or "").strip()
    has_value = bool(display and display != AWAITING_USER_INPUT)

    if not param_id:
        return _awaiting_user_provenance("unknown")

    store = reader.graph_store
    if not store.available:
        return _awaiting_user_provenance("unknown")

    try:
        param = reader.load(param_id)
    except FileNotFoundError:
        return _awaiting_user_provenance("unknown")

    meta = param.metadata
    if trace_source_type == "user_input" or (
        not trace_source_type and _is_user_input_parameter(store, param_id, meta)
    ):
        if has_value:
            return {
                "source_type": "user_input",
                "status": "resolved",
                "label": "User supplied",
                "source_ref": {"parameter_id": param_id},
            }
        return _awaiting_user_provenance("user_input", param_id=param_id)

    inputs = task.fact_store.active_facts()
    active = set(active_nodes) if active_nodes is not None else set(task.active_nodes or [])
    producers = _active_producers_for_parameter(store, param_id, inputs)
    producer_id = _select_producer(producers, active) if producers else ""

    source_type = _normalize_trace_source_type(trace_source_type)
    if source_type is None and producer_id:
        source_type = _source_type_for_producer(reader, producer_id)
    if source_type is None:
        resolution = meta.get("resolution") or parameter_resolution_for_parameter(store, param_id) or {}
        method = str(resolution.get("method", "")).strip() if isinstance(resolution, dict) else ""
        if method == "table_lookup" or lookup_resolution_for_parameter(store, param_id):
            source_type = "table_lookup"
        elif str(meta.get("parameter_class", "")).strip() == "calculated_quantity":
            source_type = "equation_output"
        else:
            source_type = "unknown"

    value_reference = resolve_parameter_value_reference(
        reader,
        param_id,
        task,
        active_nodes=active_nodes,
    )
    if value_reference is None and trace_source_ref:
        value_reference = _reference_link_from_trace_source(
            reader,
            trace_source_ref,
            source_type,
        )

    if source_type == "unknown" and value_reference is not None:
        source_type = (
            "table_lookup"
            if value_reference.get("reference_kind") == "table"
            else "equation_output"
        )

    status = "resolved" if has_value else "pending_derived"
    label = _provenance_label(
        reader,
        param_id=param_id,
        producer_id=producer_id,
        source_type=source_type,
        value_reference=value_reference,
    )
    source_ref = _source_ref_payload(
        param_id=param_id,
        producer_id=producer_id,
        source_type=source_type,
        value_reference=value_reference,
        trace_source_ref=trace_source_ref,
    )

    provenance: dict[str, Any] = {
        "source_type": source_type,
        "status": status,
        "label": label,
    }
    if source_ref:
        provenance["source_ref"] = source_ref
    return provenance


def apply_value_provenance_to_row(
    row: dict[str, Any],
    reader: StandardsReader,
    param_id: str,
    task: Task,
    *,
    display_value: str | None = None,
    active_nodes: set[str] | frozenset[str] | None = None,
    trace_source_type: str | None = None,
    trace_source_ref: str | None = None,
) -> dict[str, Any]:
    """Attach value_provenance and legacy value fields to an equation input row."""
    updated = dict(row)
    resolved_display = display_value if display_value is not None else updated.get("value")
    provenance = build_value_provenance(
        reader,
        param_id,
        task,
        display_value=str(resolved_display or ""),
        active_nodes=active_nodes,
        trace_source_type=trace_source_type,
        trace_source_ref=trace_source_ref,
    )
    updated["value_provenance"] = provenance

    status = str(provenance.get("status") or "")
    source_type = str(provenance.get("source_type") or "")

    if status == "awaiting_user_input":
        updated["value"] = AWAITING_USER_INPUT
        updated["value_status"] = "unresolved_user_input"
        updated.pop("value_reference", None)
        return updated

    if status == "pending_derived":
        updated["value"] = ""
        value_reference = resolve_parameter_value_reference(
            reader,
            param_id,
            task,
            active_nodes=active_nodes,
        )
        if value_reference is None and trace_source_ref:
            value_reference = _reference_link_from_trace_source(
                reader,
                trace_source_ref,
                source_type,
            )
        if value_reference is not None:
            updated["value_reference"] = value_reference
        updated["value_status"] = (
            "lookup_derived" if source_type == "table_lookup" else "unresolved_derived"
        )
        return updated

    updated["value_status"] = (
        "user_supplied"
        if source_type == "user_input"
        else "lookup_derived" if source_type == "table_lookup" else "equation_derived"
    )
    value_reference = resolve_parameter_value_reference(
        reader,
        param_id,
        task,
        active_nodes=active_nodes,
    )
    if value_reference is not None and source_type != "user_input":
        updated["value_reference"] = value_reference
    return updated


def _awaiting_user_provenance(
    source_type: str,
    *,
    param_id: str | None = None,
) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "source_type": source_type,
        "status": "awaiting_user_input",
        "label": AWAITING_USER_INPUT,
    }
    if param_id:
        provenance["source_ref"] = {"parameter_id": param_id}
    return provenance


def _normalize_trace_source_type(source_type: str | None) -> str | None:
    normalized = str(source_type or "").strip()
    if normalized == "system":
        return "default"
    if normalized in _VALUE_PROVENANCE_SOURCE_TYPES:
        return normalized
    return None


def _source_type_for_producer(reader: StandardsReader, producer_id: str) -> str:
    producer_id = str(producer_id or "").strip()
    if not producer_id:
        return "unknown"
    try:
        record = reader.load(producer_id)
    except FileNotFoundError:
        return "unknown"
    node_type = str(record.metadata.get("type") or "").strip()
    if node_type == "lookup":
        return "table_lookup"
    if node_type == "equation":
        return "equation_output"
    if node_type == "table":
        return "table_lookup"
    return "unknown"


def _provenance_label(
    reader: StandardsReader,
    *,
    param_id: str,
    producer_id: str,
    source_type: str,
    value_reference: dict[str, str] | None,
) -> str:
    if source_type == "table_lookup":
        if value_reference and value_reference.get("label"):
            return f"Resolved from {value_reference['label']}"
        description = _parameter_description(reader, param_id)
        if description:
            return f"Resolved from {description.lower()} table"
        return "Resolved from standards table"

    if source_type == "equation_output":
        if value_reference and value_reference.get("node_id"):
            return ""
        return ""

    return AWAITING_USER_INPUT


def _parameter_description(reader: StandardsReader, param_id: str) -> str:
    try:
        record = reader.load(param_id)
    except FileNotFoundError:
        return ""
    for key in ("description", "name", "label", "title"):
        text = str(record.metadata.get(key) or "").strip()
        if text:
            return text
    return ""


def _source_ref_payload(
    *,
    param_id: str,
    producer_id: str,
    source_type: str,
    value_reference: dict[str, str] | None,
    trace_source_ref: str | None,
) -> dict[str, str]:
    payload: dict[str, str] = {"parameter_id": param_id}
    if source_type == "equation_output":
        if producer_id:
            payload["equation_id"] = producer_id
            payload["node_id"] = producer_id
        if value_reference and value_reference.get("node_id"):
            payload["paragraph_id"] = str(value_reference["node_id"])
    elif source_type == "table_lookup":
        table_id = ""
        if value_reference and value_reference.get("node_id"):
            table_id = str(value_reference["node_id"])
        elif trace_source_ref:
            table_id = str(trace_source_ref).strip()
        if table_id:
            payload["table_id"] = table_id
            payload["node_id"] = table_id
    return payload


def _reference_link_from_trace_source(
    reader: StandardsReader,
    source_ref: str,
    source_type: str,
) -> dict[str, str] | None:
    source_ref = str(source_ref or "").strip()
    if not source_ref:
        return None
    if source_type == "table_lookup":
        return _lookup_table_reference(reader, {"id": source_ref, "lookup": {"table": source_ref}})
    if source_type == "equation_output":
        return _reference_link_from_producer(reader, source_ref)
    return _paragraph_reference_link(reader, source_ref)


def legacy_value_status_from_provenance(provenance: dict[str, Any]) -> str:
    """Map value_provenance to legacy value_status for backward compatibility."""
    status = str(provenance.get("status") or "")
    source_type = str(provenance.get("source_type") or "")
    if status == "awaiting_user_input":
        return "unresolved_user_input"
    if status == "pending_derived":
        return "lookup_derived" if source_type == "table_lookup" else "unresolved_derived"
    if source_type == "user_input":
        return "user_supplied"
    if source_type == "table_lookup":
        return "lookup_derived"
    if source_type in {"equation_output", "default"}:
        return "equation_derived"
    return "unresolved_user_input"


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
        from api.paragraph_display import paragraph_reference_label

        paragraph = paragraph_reference(record.metadata) or node_id
        label = paragraph_reference_label(record.metadata, node_id)
    except FileNotFoundError:
        paragraph = node_id
        label = node_id

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
