"""Legacy relationship field compilation (used only by migration tooling)."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import parse_dependency_node_ref
from engine.reference.graph_edge_schema import (
    ALLOWED_EDGE_METADATA,
    expand_incoming_edge_types,
    relationship_metadata,
)

LEGACY_EDGE_LIST_KEYS = (
    "requires",
    "calculates",
    "defines",
    "explains",
    "outputs",
    "contains",
    "anchors_to",
    "uses_table",
    "next_step",
    "validates",
    "located_in",
    "defined_by",
    "related_to",
    "references",
    "uses",
    "accepts",
    "depends_on",
    "converts_to",
)


def compile_legacy_metadata_edges(
    node_id: str,
    metadata: dict[str, Any],
) -> list[tuple[str, str, str, dict[str, Any] | None]]:
    """Extract edges from legacy metadata fields (pre-migration baseline)."""
    compiled: list[tuple[str, str, str, dict[str, Any] | None]] = []
    seen: set[tuple[str, str, str, str | None]] = set()

    def add_edge(
        from_id: str,
        to_id: str,
        edge_type: str,
        edge_meta: dict[str, Any] | None = None,
    ) -> None:
        alias = None
        if edge_meta and edge_meta.get("alias") is not None:
            alias = str(edge_meta["alias"])
        key = (from_id, to_id, edge_type, alias)
        if key in seen:
            return
        seen.add(key)
        compiled.append((from_id, to_id, edge_type, edge_meta))

    for edge_type in LEGACY_EDGE_LIST_KEYS:
        if edge_type == "depends_on":
            continue
        targets = metadata.get(edge_type)
        if not targets:
            continue
        if isinstance(targets, str):
            add_edge(node_id, targets, edge_type)
            continue
        if not isinstance(targets, list):
            continue
        for target in targets:
            if isinstance(target, str):
                add_edge(node_id, target, edge_type)
            elif isinstance(target, dict):
                to_id = str(
                    target.get("node_id") or target.get("to") or target.get("id") or ""
                ).strip()
                if not to_id:
                    continue
                et = str(target.get("type") or edge_type)
                edge_meta = relationship_metadata(target)
                add_edge(node_id, to_id, et, edge_meta if edge_meta else None)

    anchors_to = metadata.get("anchors_to")
    if isinstance(anchors_to, str) and anchors_to:
        add_edge(node_id, anchors_to, "anchors_to")

    for item in metadata.get("edges", []) or []:
        if not isinstance(item, dict):
            continue
        to_id = str(item.get("to") or item.get("node_id") or item.get("target") or "").strip()
        if not to_id:
            continue
        edge_type = str(item.get("type") or "related_to")
        edge_meta = relationship_metadata(item)
        direction = str(item.get("direction") or "outgoing")
        if direction == "incoming":
            add_edge(to_id, node_id, edge_type, edge_meta if edge_meta else None)
        else:
            add_edge(node_id, to_id, edge_type, edge_meta if edge_meta else None)

    for item in metadata.get("depends_on", []) or []:
        if isinstance(item, dict):
            dep_ref = str(item.get("node_id", "")).strip()
            if not dep_ref:
                continue
            dep_id, subsection = parse_dependency_node_ref(dep_ref)
            dep_type = str(item.get("dependency_type") or "requires")
            edge_meta = relationship_metadata(item)
            if subsection and "subsection" not in edge_meta:
                edge_meta = {**edge_meta, "subsection": subsection}
            add_edge(dep_id, node_id, dep_type, edge_meta if edge_meta else None)
        elif isinstance(item, str) and item.strip():
            dep_id, subsection = parse_dependency_node_ref(item.strip())
            edge_meta = {"subsection": subsection} if subsection else None
            add_edge(dep_id, node_id, "requires", edge_meta)

    for subsection in metadata.get("subsections", []) or []:
        if not isinstance(subsection, dict):
            continue
        subsection_id = str(subsection.get("id") or "").strip() or None
        for equation in subsection.get("equations", []) or []:
            if not isinstance(equation, dict):
                continue
            if str(equation.get("ref") or "").strip().lower() != "external":
                continue
            to_id = str(equation.get("node_id") or equation.get("id") or "").strip()
            if not to_id:
                continue
            edge_meta = relationship_metadata(equation)
            if subsection_id and "subsection" not in edge_meta:
                edge_meta = {**edge_meta, "subsection": subsection_id}
            add_edge(node_id, to_id, "references", edge_meta if edge_meta else None)

    for equation in metadata.get("equations", []) or []:
        if not isinstance(equation, dict):
            continue
        if str(equation.get("ref") or "").strip().lower() != "external":
            continue
        to_id = str(equation.get("node_id") or equation.get("id") or "").strip()
        if not to_id:
            continue
        edge_meta = relationship_metadata(equation)
        add_edge(node_id, to_id, "references", edge_meta if edge_meta else None)

    for item in metadata.get("hierarchy", []) or []:
        if isinstance(item, dict):
            parent_id = str(item.get("node_id") or "").strip()
            if parent_id:
                add_edge(parent_id, node_id, "contains")

    parent_node_id = str(metadata.get("parent_node_id") or "").strip()
    if parent_node_id:
        add_edge(parent_node_id, node_id, "contains")

    return compiled
