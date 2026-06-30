"""Value provenance index for developer inspection."""

from __future__ import annotations

from typing import Any

from api.node_provenance import enrich_display_blocks_provenance, provenance_for_node
from api.output_blocks import build_display_outputs
from engine.inspection.models import ValueProvenanceRecord
from engine.reference.standards_reader import StandardsReader
from models.task import Task


def _block_display_value(block: dict[str, Any]) -> str:
    for key in ("value", "text", "title", "content"):
        value = block.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()[:200]
    return str(block.get("id", ""))


def _node_id_from_block(block: dict[str, Any]) -> str | None:
    source_node = block.get("source_node")
    if source_node:
        return str(source_node)

    nomenclature = block.get("nomenclature_reference")
    if isinstance(nomenclature, dict) and nomenclature.get("node_id"):
        return str(nomenclature["node_id"])

    reference_links = block.get("reference_links")
    if isinstance(reference_links, list) and reference_links:
        first = reference_links[0]
        if isinstance(first, dict) and first.get("node_id"):
            return str(first["node_id"])

    block_id = str(block.get("id", ""))
    prefixes = (
        "node-activation-assumptions-",
        "node-activation-equation-",
        "path-preview-equation-",
        "path-preview-intro-",
        "equation-",
        "reference-",
        "table-steps-",
        "table-intermediates-",
    )
    for prefix in prefixes:
        if block_id.startswith(prefix):
            return block_id[len(prefix) :]

    if block_id in {"mawp-pressure-design-equation", "mawp-formula-equation", "mawp-substituted-equation"}:
        return "B313-MAWP-CALCULATION"
    if block_id == "mawp-conclusion":
        return "B313-MAWP-CALCULATION"

    return None


def _source_field_for_block(block: dict[str, Any]) -> str | None:
    block_type = str(block.get("type") or "")
    block_id = str(block.get("id", ""))

    if block_id.startswith("node-activation-assumptions-"):
        return "assumptions"
    if block_type == "equation":
        if block.get("display"):
            return "display_latex"
        return "sympy"
    if block_type == "reference":
        return "purpose"
    if block_type == "result":
        return "title"
    if block_type == "text":
        if block.get("variant") == "assumption":
            return "assumptions"
        return "body"
    if block_type == "table":
        return "title"
    if block_type == "graph":
        return "title"
    return None


def _graph_neighbors(reader: StandardsReader, node_id: str) -> tuple[list[str], list[str]]:
    store = reader.graph_store
    if not store.available:
        return [], []
    store.load()
    upstream = [edge.from_id for edge in store.incoming(node_id)]
    downstream = [edge.to_id for edge in store.outgoing(node_id)]
    return upstream, downstream


def _transformation_history(task: Task, node_id: str) -> list[dict[str, Any]]:
    raw_trace = task.outputs.get("_execution_trace")
    if not isinstance(raw_trace, list):
        return []
    for item in raw_trace:
        if not isinstance(item, dict) or str(item.get("node_id")) != node_id:
            continue
        trace = item.get("trace")
        if not isinstance(trace, dict):
            return []
        history: list[dict[str, Any]] = []
        if trace.get("calculation"):
            history.append({"kind": "calculation", "detail": trace["calculation"]})
        if trace.get("render_steps"):
            history.append({"kind": "render_steps", "steps": trace["render_steps"]})
        if trace.get("lookup"):
            history.append({"kind": "lookup", "detail": trace["lookup"]})
        return history
    return []


def extended_provenance_for_block(
    block: dict[str, Any],
    reader: StandardsReader,
    task: Task,
) -> ValueProvenanceRecord | None:
    node_id = _node_id_from_block(block)
    if not node_id:
        return ValueProvenanceRecord(
            display_id=str(block.get("id", "")),
            display_value=_block_display_value(block),
            source_node="",
            source_property="",
            missing=True,
        )

    source_field = _source_field_for_block(block) or "outputs.value"
    base = provenance_for_node(reader, node_id, source_field=source_field)
    upstream, downstream = _graph_neighbors(reader, node_id)
    generated_by = base.get("generated_by") if base else (upstream[0] if upstream else None)
    consumed_by = base.get("consumed_by") if base else downstream

    trace_history = _transformation_history(task, node_id)

    return ValueProvenanceRecord(
        display_id=str(block.get("id", "")),
        display_value=_block_display_value(block),
        source_node=node_id,
        source_property=source_field,
        generated_by=generated_by,
        consumed_by=list(consumed_by or []),
        transformation_history=trace_history,
        missing=False,
    )


def build_provenance_index(
    task: Task,
    reader: StandardsReader | None,
) -> list[ValueProvenanceRecord]:
    if reader is None:
        return []

    blocks = build_display_outputs(task, standards_root=reader.standards_root, reader=reader)
    enrich_display_blocks_provenance(blocks, reader)
    records: list[ValueProvenanceRecord] = []
    for block in blocks:
        record = extended_provenance_for_block(block, reader, task)
        if record is not None:
            records.append(record)
    return records
