"""Compile micro-graph node metadata into semantic edges."""

from __future__ import annotations

from typing import Any

from engine.reference.node_types import MICRO_GRAPH_TYPES, is_micro_graph_node

LEGACY_SECTION_ALIASES = {
    "B313-304.1.1": "B313-304.1.1-SECTION",
    "B313-304.1.2": "B313-304.1.2-SECTION",
    "B313-304.1.3": "B313-304.1.3-SECTION",
}

EDGE_LIST_KEYS = (
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


def compile_metadata_edges(
    node_id: str,
    metadata: dict[str, Any],
) -> list[tuple[str, str, str, dict[str, Any] | None]]:
    """Extract edges from metadata fields and explicit edges block."""
    compiled: list[tuple[str, str, str, dict[str, Any] | None]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_edge(
        from_id: str,
        to_id: str,
        edge_type: str,
        edge_meta: dict[str, Any] | None = None,
    ) -> None:
        key = (from_id, to_id, edge_type)
        if key in seen:
            return
        seen.add(key)
        compiled.append((from_id, to_id, edge_type, edge_meta))

    for edge_type in EDGE_LIST_KEYS:
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
                when = target.get("when") if isinstance(target.get("when"), dict) else None
                edge_meta: dict[str, Any] = {}
                if when:
                    edge_meta["when"] = when
                if "priority" in target:
                    edge_meta["priority"] = target["priority"]
                if "factor" in target:
                    edge_meta["factor"] = target["factor"]
                if "offset" in target:
                    edge_meta["offset"] = target["offset"]
                et = str(target.get("type") or edge_type)
                add_edge(node_id, to_id, et, edge_meta if edge_meta else None)

    anchors_to = metadata.get("anchors_to")
    if isinstance(anchors_to, str) and anchors_to:
        add_edge(node_id, anchors_to, "anchors_to")

    for item in metadata.get("edges", []) or []:
        if not isinstance(item, dict):
            continue
        to_id = str(item.get("to") or item.get("node_id") or "").strip()
        if not to_id:
            continue
        edge_type = str(item.get("type") or "related_to")
        when = item.get("when") if isinstance(item.get("when"), dict) else None
        edge_meta = {"when": when} if when else None
        direction = str(item.get("direction") or "outgoing")
        if direction == "incoming":
            add_edge(to_id, node_id, edge_type, edge_meta)
        else:
            add_edge(node_id, to_id, edge_type, edge_meta)

    for item in metadata.get("depends_on", []) or []:
        if isinstance(item, dict):
            dep_id = str(item.get("node_id", "")).strip()
            if not dep_id:
                continue
            dep_type = str(item.get("dependency_type") or "requires")
            when = item.get("when") if isinstance(item.get("when"), dict) else None
            edge_meta = {"when": when} if when else None
            add_edge(dep_id, node_id, dep_type, edge_meta)
        elif isinstance(item, str) and item.strip():
            add_edge(item.strip(), node_id, "requires")

    return compiled


def node_aliases(node_id: str, metadata: dict[str, Any]) -> list[str]:
    aliases: list[str] = []
    slug = str(metadata.get("slug", "")).strip()
    if slug and slug != node_id:
        aliases.append(slug)
    legacy_alias = LEGACY_SECTION_ALIASES.get(node_id)
    if legacy_alias:
        aliases.append(legacy_alias)
    for item in metadata.get("aliases", []) or []:
        if isinstance(item, str) and item.strip() and item.strip() != node_id:
            aliases.append(item.strip())
    return aliases
