"""Validate knowledge-graph relationship edges against the taxonomy."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_edge_schema import (
    ALLOWED_EDGE_METADATA,
    CANONICAL_EDGE_TYPES,
    EDGE_ROUTING_KEYS,
    REVERSE_ONLY_QUERY_TYPES,
    STORED_EDGE_TYPES,
    edge_target,
)
from engine.reference.relationship_taxonomy import (
    DISCOURAGED_GENERIC_TYPES,
    KNOWLEDGE_EDGE_TYPES,
    LEGACY_TRANSPORT_TYPES,
    RUNTIME_ONLY_EDGE_TYPES,
    normalize_authoring_edge,
    validate_taxonomy_edge,
)


def validate_edge_item(
    item: dict[str, Any],
    *,
    source_node_type: str = "",
    allow_legacy: bool = False,
) -> list[str]:
    """Return validation issues for one edge dict."""
    issues: list[str] = []
    if not isinstance(item, dict):
        return ["edge must be a mapping"]
    edge_type = str(item.get("type") or "").strip()
    target = edge_target(item)
    if not edge_type:
        issues.append("missing type")
    elif edge_type in REVERSE_ONLY_QUERY_TYPES:
        issues.append(f"reverse type must not be stored: {edge_type}")
    elif not allow_legacy and edge_type in LEGACY_TRANSPORT_TYPES:
        if edge_type in DISCOURAGED_GENERIC_TYPES:
            issues.append(
                f"legacy transport edge type {edge_type!r}; use taxonomy types "
                "(run scripts/migrate_relationships_to_taxonomy.py)"
            )
    elif edge_type not in CANONICAL_EDGE_TYPES:
        issues.append(f"unknown type: {edge_type}")
    elif edge_type not in STORED_EDGE_TYPES and edge_type not in LEGACY_TRANSPORT_TYPES:
        issues.append(f"type not storable: {edge_type}")
    if not target:
        issues.append("missing target")
    for key in item:
        if key in EDGE_ROUTING_KEYS:
            continue
        if key not in ALLOWED_EDGE_METADATA:
            issues.append(f"disallowed metadata key: {key}")

    normalized = normalize_authoring_edge(item, source_node_type=source_node_type, allow_legacy=allow_legacy)
    if normalized is None and edge_type in LEGACY_TRANSPORT_TYPES and not allow_legacy:
        issues.append(f"could not normalize legacy edge type: {edge_type}")

    if source_node_type and normalized:
        issues.extend(
            validate_taxonomy_edge(normalized, source_node_type=source_node_type)
        )
    elif source_node_type and edge_type in KNOWLEDGE_EDGE_TYPES:
        issues.extend(
            validate_taxonomy_edge(item, source_node_type=source_node_type)
        )

    if edge_type in RUNTIME_ONLY_EDGE_TYPES:
        issues.append(f"runtime-only edge type not allowed on knowledge nodes: {edge_type}")

    return issues


def validate_edges_for_node(
    metadata: dict[str, Any],
    *,
    allow_legacy: bool = False,
) -> list[str]:
    """Validate all edges on a node metadata dict."""
    source_node_type = str(metadata.get("type") or "")
    issues: list[str] = []
    for item in metadata.get("edges") or []:
        if not isinstance(item, dict):
            issues.append("edge entry must be a mapping")
            continue
        for issue in validate_edge_item(
            item,
            source_node_type=source_node_type,
            allow_legacy=allow_legacy,
        ):
            issues.append(issue)
    return issues
