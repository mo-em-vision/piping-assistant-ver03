"""Compile micro-graph node metadata into semantic edges."""

from __future__ import annotations

from typing import Any

from engine.reference.b313_legacy_aliases import build_b313_legacy_aliases
from engine.reference.graph_edge_schema import (
    ALLOWED_EDGE_METADATA,
    CANONICAL_EDGE_TYPES,
    EDGE_ROUTING_KEYS,
    STORED_EDGE_TYPES,
    edge_target,
    relationship_metadata,
)
from engine.reference.node_types import MICRO_GRAPH_TYPES, is_micro_graph_node

LEGACY_SECTION_ALIASES = {
    "304.1.1": "304.1.1-SECTION",
    "304.1.2": "304.1.2-SECTION",
    "304.1.3": "304.1.3-SECTION",
    "B313-304.1.1": "304.1.1-SECTION",
    "B313-304.1.2": "304.1.2-SECTION",
    "B313-304.1.3": "304.1.3-SECTION",
}

LEGACY_NODE_ID_ALIASES = build_b313_legacy_aliases()

# Deprecated — kept for import compatibility during tooling transition.
EDGE_LIST_KEYS: tuple[str, ...] = ("edges",)


def parse_dependency_node_ref(node_id: str) -> tuple[str, str | None]:
    """Split ``node_id/subsection`` into a graph node id and optional subsection."""
    text = str(node_id).strip()
    if not text or "/" not in text:
        return text, None
    base, subsection = text.rsplit("/", 1)
    if not base or not subsection:
        return text, None
    return base, subsection


def compile_metadata_edges(
    node_id: str,
    metadata: dict[str, Any],
) -> list[tuple[str, str, str, dict[str, Any] | None]]:
    """Extract outgoing edges from the canonical ``edges`` metadata field."""
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

    for item in metadata.get("edges", []) or []:
        if not isinstance(item, dict):
            continue
        to_id = edge_target(item)
        if not to_id:
            continue
        dep_id, subsection = parse_dependency_node_ref(to_id)
        to_id = dep_id
        edge_type = str(item.get("type") or "").strip()
        if not edge_type:
            continue
        if edge_type not in CANONICAL_EDGE_TYPES:
            continue
        if edge_type.endswith("_by"):
            continue
        edge_meta = relationship_metadata(item)
        if subsection and "subsection" not in edge_meta:
            edge_meta = {**edge_meta, "subsection": subsection}
        add_edge(node_id, to_id, edge_type, edge_meta if edge_meta else None)

    return compiled


def validate_edge_item(item: dict[str, Any]) -> list[str]:
    """Return validation issues for one edge dict."""
    issues: list[str] = []
    edge_type = str(item.get("type") or "").strip()
    target = edge_target(item)
    if not edge_type:
        issues.append("missing type")
    elif edge_type not in CANONICAL_EDGE_TYPES:
        issues.append(f"unknown type: {edge_type}")
    elif edge_type.endswith("_by"):
        issues.append(f"reverse type must not be stored: {edge_type}")
    elif edge_type not in STORED_EDGE_TYPES:
        issues.append(f"type not storable: {edge_type}")
    if not target:
        issues.append("missing target")
    for key in item:
        if key in EDGE_ROUTING_KEYS:
            continue
        if key not in ALLOWED_EDGE_METADATA:
            issues.append(f"disallowed metadata key: {key}")
    return issues


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
    for legacy_id, target_id in LEGACY_NODE_ID_ALIASES.items():
        if node_id == target_id:
            aliases.append(legacy_id)
    return aliases
