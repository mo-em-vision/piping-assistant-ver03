"""Resolve workflow definition anchor nodes for planning refresh."""

from __future__ import annotations

from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id
from engine.planner.tools import GraphTools
from engine.reference.graph_edge_schema import workflow_anchor_target
from engine.reference.standards_reader import StandardsReader


def resolve_activated_definition_node(
    reader: StandardsReader,
    workflow_id: str,
    *,
    execution_order: tuple[str, ...] | list[str] | None = None,
) -> str | None:
    """Return the workflow's primary definition/section node."""
    slug = normalize_root_id(workflow_id)
    resolved_slug = resolve_workflow_node_id(slug)
    engine = GraphEngine()
    if engine.uses_micro_graph(reader, resolved_slug):
        store = engine._micro_engine(reader)
        if store is not None:
            resolved = engine._resolve_micro_root(resolved_slug, reader)
            wf = store.store.get_node(resolved)
            if wf is not None:
                anchor = workflow_anchor_target(wf.metadata)
                if isinstance(anchor, str):
                    return anchor
                anchors = wf.metadata.get("anchors_to")
                if isinstance(anchors, str):
                    return anchors
    try:
        root = reader.load(slug)
    except FileNotFoundError:
        return None

    for entry in root.metadata.get("entry_points", []) or []:
        if isinstance(entry, dict) and str(entry.get("role", "")) == "definition_anchor":
            parameter = entry.get("parameter")
            if parameter:
                return str(parameter)
            paragraph = entry.get("paragraph")
            if paragraph:
                return str(paragraph)

    anchor = workflow_anchor_target(root.metadata)
    if isinstance(anchor, str):
        return anchor

    for item in root.metadata.get("depends_on", []) or []:
        if not isinstance(item, dict):
            continue
        node_id = item.get("node_id")
        if not node_id:
            continue
        try:
            record = reader.load(str(node_id))
        except FileNotFoundError:
            continue
        if str(record.metadata.get("type", "")) in {"definition", "paragraph"}:
            return str(node_id)

    order = execution_order
    if order is None:
        graph = GraphTools(reader)
        order = graph.preview_plan(
            task_id="bootstrap",
            root_id=resolved_slug,
            inputs={},
        ).execution_order

    for node_id in order:
        try:
            record = reader.load(node_id)
        except FileNotFoundError:
            continue
        if str(record.metadata.get("type", "")) in {"definition", "paragraph"}:
            return node_id
    return None
