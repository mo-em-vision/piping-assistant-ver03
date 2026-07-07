"""Resolve equation requires entries through quantity/designation concepts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.graph_store import GraphStore
from engine.graph.param_priority import require_target_id
from engine.reference.graph_edge_schema import relationship_metadata
from engine.reference.relationship_taxonomy import PARAMETER_CONCEPT_TRAVERSAL_TYPES, REQUIRES_TRAVERSAL_TYPES
from engine.reference.node_types import (
    is_designation_node,
    is_quantity_node,
)


@dataclass(frozen=True)
class RequireBinding:
    """One sympy input resolved from a requires entry."""

    concept_id: str
    param_id: str
    sympy_symbol: str
    metadata: dict[str, Any]


def require_sympy_alias(item: Any, *, fallback_symbol: str = "") -> str:
    if isinstance(item, dict):
        for key in ("alias", "symbol"):
            alias = str(item.get(key) or "").strip()
            if alias:
                return alias
    return fallback_symbol


def is_concept_node(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    return is_quantity_node(metadata, node_type) or is_designation_node(metadata, node_type)


def find_parameter_for_concept(
    store: GraphStore,
    concept_id: str,
    *,
    alias: str = "",
) -> str | None:
    """Map a quantity/designation node to the parameter that references it."""
    candidates: list[str] = []
    for edge in store.incoming(concept_id, edge_types=PARAMETER_CONCEPT_TRAVERSAL_TYPES):
        param_id = edge.from_id
        if store.node_type(param_id) != "parameter":
            continue
        candidates.append(param_id)
        if alias and str(store.metadata(param_id).get("symbol", "")) == alias:
            return param_id
    if len(candidates) == 1:
        return candidates[0]
    if alias:
        for param_id in candidates:
            if str(store.metadata(param_id).get("symbol", "")) == alias:
                return param_id
    return candidates[0] if candidates else None


def resolve_require_binding(
    store: GraphStore,
    item: Any,
) -> RequireBinding | None:
    target_id = require_target_id(item)
    if not target_id:
        return None

    edge_meta = relationship_metadata(item) if isinstance(item, dict) else {}
    node_type = store.node_type(target_id) or ""
    node_meta = store.metadata(target_id)

    if is_concept_node(node_meta, node_type):
        alias = require_sympy_alias(item)
        param_id = find_parameter_for_concept(store, target_id, alias=alias)
        if not param_id:
            return None
        param_meta = store.metadata(param_id)
        sympy_symbol = alias or str(param_meta.get("symbol", "")).strip()
        if not sympy_symbol:
            return None
        return RequireBinding(target_id, param_id, sympy_symbol, edge_meta)

    param_meta = store.metadata(target_id)
    sympy_symbol = require_sympy_alias(item, fallback_symbol=str(param_meta.get("symbol", "")).strip())
    if not sympy_symbol:
        return None
    return RequireBinding(target_id, target_id, sympy_symbol, edge_meta)


def node_requires_items(store: GraphStore, node_id: str) -> list[dict[str, Any]]:
    """Return requires entries from compiled ``requires`` edges on a node."""
    items: list[dict[str, Any]] = []
    for edge in store.outgoing(node_id, edge_types=REQUIRES_TRAVERSAL_TYPES):
        item: dict[str, Any] = {"target": edge.to_id, "node_id": edge.to_id}
        if edge.metadata:
            item.update(edge.metadata)
        items.append(item)
    return items


def resolve_requires_for_node(
    store: GraphStore,
    node_id: str,
    metadata: dict[str, Any] | None = None,
) -> list[RequireBinding]:
    meta = metadata if metadata is not None else store.metadata(node_id)
    requires = meta.get("requires")
    if not requires:
        requires = node_requires_items(store, node_id)
    return resolve_require_bindings(store, requires)


def resolve_require_bindings(store: GraphStore, requires: Any) -> list[RequireBinding]:
    if not requires:
        return []
    if isinstance(requires, str):
        requires = [requires]
    if not isinstance(requires, list):
        return []

    bindings: list[RequireBinding] = []
    for item in requires:
        binding = resolve_require_binding(store, item)
        if binding is not None:
            bindings.append(binding)
    return bindings


def resolve_priority_target(store: GraphStore, item: Any) -> str | None:
    """Return the parameter node id used for collection priority."""
    binding = resolve_require_binding(store, item)
    return binding.param_id if binding else require_target_id(item)
