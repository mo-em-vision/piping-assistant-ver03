"""Canonical graph edge types and metadata for knowledge node relationships."""

from __future__ import annotations

from typing import Any

CANONICAL_EDGE_TYPES = frozenset(
    {
        "parent",
        "child",
        "contains",
        "contained_by",
        "references",
        "referenced_by",
        "parameter",
        "equation",
        "material",
        "table",
        "figure",
        "note",
        "dataset",
        "implements",
        "implemented_by",
        "depends_on",
        "dependency_of",
        "uses",
        "used_by",
        "requires",
        "required_by",
        "next",
        "previous",
        "related_to",
        "derived_from",
        "alias_of",
        "has_dimension",
        "dimension_of",
        "introduced_by",
        "introduces",
        "allows_unit",
        "allowed_by",
        "converts_to",
        "converted_from",
        "belongs_to_dimension",
        "includes_unit",
        "has_parameter",
        "parameter_of",
        "specializes",
        "generalizes",
        "constrained_by",
        "constrains",
    }
)

# Outgoing types that may be stored on nodes (exclude *_by reverse-only query types).
STORED_EDGE_TYPES = frozenset(
    edge_type for edge_type in CANONICAL_EDGE_TYPES if not edge_type.endswith("_by")
)

ALLOWED_EDGE_METADATA = frozenset(
    {
        "when",
        "alias",
        "role",
        "subsection",
        "factor",
        "offset",
        "reason",
    }
)

EDGE_ROUTING_KEYS = frozenset({"type", "target", "to", "node_id", "id", "direction"})

REVERSE_EDGE_TYPE: dict[str, str] = {
    "parent": "child",
    "child": "parent",
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
    "dependency_of": "depends_on",
    "uses": "used_by",
    "used_by": "uses",
    "requires": "required_by",
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
    "allows_unit": "allowed_by",
    "allowed_by": "allows_unit",
    "converts_to": "converted_from",
    "converted_from": "converts_to",
    "belongs_to_dimension": "includes_unit",
    "includes_unit": "belongs_to_dimension",
    "has_parameter": "parameter_of",
    "parameter_of": "has_parameter",
    "specializes": "generalizes",
    "generalizes": "specializes",
    "constrained_by": "constrains",
    "constrains": "constrained_by",
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
    for item in iter_stored_edges(metadata):
        if str(item.get("type") or "") != "references":
            continue
        target = edge_target(item)
        if target:
            return target
    return None


def expand_incoming_edge_types(edge_types: set[str] | None) -> set[str] | None:
    """Map reverse query types (e.g. referenced_by) to stored outgoing types."""
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
    return expanded
