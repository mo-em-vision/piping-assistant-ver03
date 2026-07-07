"""Parameter collection priority from equation requires lists."""

from __future__ import annotations

from typing import Any

from engine.graph.graph_store import GraphStore
from engine.reference.node_types import is_lookup_node
from engine.reference.relationship_taxonomy import REQUIRES_TRAVERSAL_TYPES
from engine.reference.parameter_metadata import (
    parameter_concept_id,
    parameter_defined_in,
    prepare_parameter_metadata,
)

_DEFAULT_PRIORITY = 100

__all__ = [
    "normalize_require_ids",
    "parameter_collection_priority",
    "parameter_concept_id",
    "parameter_defined_in",
    "prepare_parameter_metadata",
    "require_entry_priority",
    "require_target_id",
]


def require_target_id(item: Any) -> str | None:
    """Extract a parameter node id from a requires-list entry."""
    if isinstance(item, str):
        target = item.strip()
        return target or None
    if isinstance(item, dict):
        for key in ("node_id", "id", "to", "target", "parameter"):
            value = item.get(key)
            if value is not None:
                target = str(value).strip()
                if target:
                    return target
    return None


def require_entry_priority(item: Any) -> int | None:
    """Extract priority from a requires-list entry, if present."""
    if not isinstance(item, dict) or "priority" not in item:
        return None
    try:
        return int(item["priority"])
    except (TypeError, ValueError):
        return None


def normalize_require_ids(requires: Any) -> list[str]:
    """Return parameter node ids from a requires metadata list."""
    if not requires:
        return []
    if isinstance(requires, str):
        target = requires.strip()
        return [target] if target else []
    if not isinstance(requires, list):
        return []
    ids: list[str] = []
    for item in requires:
        target = require_target_id(item)
        if target:
            ids.append(target)
    return ids


def _is_equation_priority_source(store: GraphStore, node_id: str) -> bool:
    """Only calculation equations assign collection priority; not lookups."""
    node = store.get_node(node_id)
    if node is None or node.node_type != "equation":
        return False
    return not is_lookup_node(node.metadata, node.node_type)


def _priority_from_metadata_requires(
    store: GraphStore,
    param_node_id: str,
    active_nodes: set[str],
) -> int | None:
    from engine.graph.relationship_resolver import node_requires_items, resolve_priority_target

    best: int | None = None
    for node_id in active_nodes:
        if not _is_equation_priority_source(store, node_id):
            continue
        node = store.get_node(node_id)
        if node is None:
            continue
        requires_items = node.metadata.get("requires") or node_requires_items(store, node_id)
        for item in requires_items:
            if resolve_priority_target(store, item) != param_node_id:
                continue
            priority = require_entry_priority(item)
            if priority is None:
                edge_priority = _priority_from_requires_edges(store, param_node_id, {node_id})
                if edge_priority is not None:
                    priority = edge_priority
                else:
                    continue
            if best is None or priority < best:
                best = priority
    return best


def _priority_from_resolved_requires(
    store: GraphStore,
    param_node_id: str,
    active_nodes: set[str],
) -> int | None:
    from engine.graph.relationship_resolver import node_requires_items, resolve_require_binding

    best: int | None = None
    for node_id in active_nodes:
        if not _is_equation_priority_source(store, node_id):
            continue
        node = store.get_node(node_id)
        if node is None:
            continue
        requires_items = node.metadata.get("requires") or node_requires_items(store, node_id)
        for item in requires_items:
            binding = resolve_require_binding(store, item)
            if binding is None or binding.param_id != param_node_id:
                continue
            priority = require_entry_priority(item)
            if priority is None:
                continue
            if best is None or priority < best:
                best = priority
    return best


def _priority_from_requires_edges(
    store: GraphStore,
    param_node_id: str,
    active_nodes: set[str],
) -> int | None:
    best: int | None = None
    for edge in store.incoming(param_node_id, edge_types=REQUIRES_TRAVERSAL_TYPES):
        if edge.from_id not in active_nodes:
            continue
        if not _is_equation_priority_source(store, edge.from_id):
            continue
        raw = edge.metadata.get("priority") if edge.metadata else None
        if raw is None:
            continue
        try:
            priority = int(raw)
        except (TypeError, ValueError):
            continue
        if best is None or priority < best:
            best = priority
    return best


def parameter_collection_priority(
    store: GraphStore,
    param_node_id: str,
    active_nodes: set[str] | frozenset[str] | None = None,
) -> int:
    """Resolve collection priority from active calculation equations' requires lists."""
    active = set(active_nodes) if active_nodes is not None else None

    if active is not None:
        edge_priority = _priority_from_requires_edges(store, param_node_id, active)
        if edge_priority is not None:
            return edge_priority
        resolved_priority = _priority_from_resolved_requires(store, param_node_id, active)
        if resolved_priority is not None:
            return resolved_priority
        meta_priority = _priority_from_metadata_requires(store, param_node_id, active)
        if meta_priority is not None:
            return meta_priority

    return _DEFAULT_PRIORITY
