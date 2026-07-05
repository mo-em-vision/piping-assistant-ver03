"""Canonical graph edge types and metadata for knowledge node relationships."""

from __future__ import annotations

from typing import Any

from engine.reference.relationship_taxonomy import (
    KNOWLEDGE_EDGE_TYPES,
    LEGACY_TRANSPORT_TYPES,
    expand_edge_types_for_query,
)

# Structural + legacy transport + taxonomy knowledge types.
CANONICAL_EDGE_TYPES = frozenset(
    {
        # Legacy transport (import/migration boundary only)
        *LEGACY_TRANSPORT_TYPES,
        # Reverse query types for legacy transport
        "referenced_by",
        "required_by",
        "contained_by",
        "dependency_of",
        "implemented_by",
        "used_by",
        "allowed_by",
        "converted_from",
        "includes_unit",
        "dimension_of",
        "parameter_of",
        "constrained_by",
        # Taxonomy knowledge types
        *KNOWLEDGE_EDGE_TYPES,
        # Additional ontology aliases used in packs
        "introduces",
        "dimension_of",
    }
)

# Reverse-only types for graph query (must not appear in on-disk YAML edges).
REVERSE_ONLY_QUERY_TYPES = frozenset(
    {
        "referenced_by",
        "required_by",
        "contained_by",
        "dependency_of",
        "implemented_by",
        "allowed_by",
        "converted_from",
        "includes_unit",
        "dimension_of",
        "parameter_of",
        "constrained_by",
        "used_by_lookup",
    }
)

# Outgoing types that may be stored on nodes (exclude reverse-only query types).
STORED_EDGE_TYPES = frozenset(
    edge_type for edge_type in CANONICAL_EDGE_TYPES if edge_type not in REVERSE_ONLY_QUERY_TYPES
)

ALLOWED_EDGE_METADATA = frozenset(
    {
        "when",
        "alias",
        "role",
        "subsection",
        "factor",
        "offset",
        "equation",
        "reason",
        "required",
    }
)

EDGE_ROUTING_KEYS = frozenset({"type", "target", "to", "node_id", "id", "direction"})

REVERSE_EDGE_TYPE: dict[str, str] = {
    "parent": "child",
    "child": "parent",
    "contains_paragraph": "contained_by",
    "contains_table": "contained_by",
    "contains": "contained_by",
    "contained_by": "contains",
    "references": "referenced_by",
    "referenced_by": "references",
    "parameter": "parameter",
    "equation": "equation",
    "material": "material",
    "table": "table",
    "figure": "figure",
    "note": "note",
    "dataset": "dataset",
    "implements": "implemented_by",
    "implemented_by": "implements",
    "depends_on": "dependency_of",
    "depends_on_equation": "dependency_of",
    "dependency_of": "depends_on",
    "uses": "used_by",
    "used_by": "uses",
    "requires": "required_by",
    "requires_parameter": "required_by",
    "required_by": "requires",
    "next": "previous",
    "previous": "next",
    "related_to": "related_to",
    "derived_from": "derived_from",
    "alias_of": "alias_of",
    "has_dimension": "dimension_of",
    "dimension_of": "has_dimension",
    "introduced_by": "introduces",
    "introduces": "introduced_by",
    "introduces_parameter": "introduced_by",
    "allows_unit": "allowed_by",
    "allowed_by": "allows_unit",
    "converts_to": "converted_from",
    "converted_from": "converts_to",
    "belongs_to_dimension": "includes_unit",
    "includes_unit": "belongs_to_dimension",
    "has_parameter": "parameter_of",
    "parameter_of": "has_parameter",
    "has_concept": "related_to",
    "specializes": "generalizes",
    "generalizes": "specializes",
    "constrained_by": "constrains",
    "constrains": "constrained_by",
    "constrains_parameter": "constrained_by",
    "calculates_parameter": "required_by",
    "authorized_by": "referenced_by",
    "belongs_to_authority": "referenced_by",
    "starts_from_paragraph": "referenced_by",
    "references_equation": "equation",
    "references_table": "table",
    "may_use_equation": "equation",
    "may_use_lookup": "lookup",
    "reads_table": "used_by_lookup",
    "used_by_lookup": "reads_table",
    "returns_parameter": "required_by",
}

FORWARD_EDGE_TYPE: dict[str, str] = {value: key for key, value in REVERSE_EDGE_TYPE.items()}

DEPRECATED_TOP_LEVEL_RELATIONSHIP_KEYS = frozenset(
    {
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
        "hierarchy",
        "incoming",
        "outgoing",
        "parents",
        "children",
        "links",
        "connections",
        "related",
    }
)


def edge_target(item: dict[str, Any]) -> str:
    return str(item.get("target") or item.get("to") or item.get("node_id") or item.get("id") or "").strip()


def relationship_metadata(item: dict[str, Any]) -> dict[str, Any]:
    """Return metadata stored on the compiled edge (non-routing keys only)."""
    meta: dict[str, Any] = {}
    for key, value in item.items():
        if key in EDGE_ROUTING_KEYS:
            continue
        if key == "when" and not isinstance(value, dict):
            continue
        if key in ALLOWED_EDGE_METADATA:
            meta[key] = value
    return meta


def iter_stored_edges(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    edges = metadata.get("edges")
    if not isinstance(edges, list):
        return []
    return [item for item in edges if isinstance(item, dict)]


def edge_targets(metadata: dict[str, Any], *edge_types: str) -> list[str]:
    wanted = set(edge_types)
    targets: list[str] = []
    for item in iter_stored_edges(metadata):
        edge_type = str(item.get("type") or "").strip()
        if edge_type not in wanted:
            continue
        target = edge_target(item)
        if target:
            targets.append(target)
    return targets


def dimension_allowed_unit_ids(metadata: dict[str, Any]) -> list[str]:
    """Return unit node ids allowed for a dimension (prefers ``allows_unit`` edges)."""
    allowed = edge_targets(metadata, "allows_unit")
    if allowed:
        return allowed
    return edge_targets(metadata, "references")


def workflow_anchor_target(metadata: dict[str, Any]) -> str | None:
    """Return the primary section anchor referenced by a workflow node."""
    anchor_types = ("starts_from_paragraph", "references")
    for item in iter_stored_edges(metadata):
        edge_type = str(item.get("type") or "")
        if edge_type not in anchor_types:
            continue
        if edge_type == "references":
            role = str(item.get("role") or "")
            if role and role != "starts_from_paragraph":
                continue
        target = edge_target(item)
        if target:
            return target
    for entry in metadata.get("entry_points") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("role") or "") != "definition_anchor":
            continue
        paragraph = str(entry.get("paragraph") or "").strip()
        if paragraph:
            return paragraph
    return None


def expand_incoming_edge_types(edge_types: set[str] | None) -> set[str] | None:
    """Map reverse query types and taxonomy/legacy aliases for graph_store lookups."""
    if edge_types is None:
        return None
    expanded: set[str] = set()
    for edge_type in edge_types:
        expanded.add(edge_type)
        if edge_type.endswith("_by"):
            forward = FORWARD_EDGE_TYPE.get(edge_type)
            if forward:
                expanded.add(forward)
        else:
            reverse = REVERSE_EDGE_TYPE.get(edge_type)
            if reverse and reverse != edge_type:
                expanded.add(reverse)
    return expand_edge_types_for_query(expanded)
