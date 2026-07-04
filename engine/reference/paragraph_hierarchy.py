"""Paragraph ancestor hierarchy helpers for standards section nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.reference.standards_reader import StandardsReader


def paragraph_reference(metadata: dict[str, Any]) -> str:
    """Return the standards paragraph id for display and provenance."""
    return str(
        metadata.get("paragraph_number")
        or metadata.get("paragraph")
        or metadata.get("id")
        or ""
    ).strip()


def section_label(metadata: dict[str, Any]) -> str | None:
    """Return the top section label from legacy ``section`` or ancestor chain metadata."""
    section = str(metadata.get("section", "")).strip()
    if section:
        return section
    chain = metadata.get("hierarchy_chain")
    if isinstance(chain, list) and chain:
        for item in reversed(chain):
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                if title:
                    return title
    for item in reversed(hierarchy_entries(metadata)):
        title = str(item.get("title", "")).strip()
        if title:
            return title
    return None


def hierarchy_parent_id(metadata: dict[str, Any]) -> str:
    """Return the immediate parent paragraph id from ``hierarchy.parent``."""
    hierarchy = metadata.get("hierarchy")
    if not isinstance(hierarchy, dict):
        return ""
    parent = str(hierarchy.get("parent") or "").strip()
    if not parent or parent.lower() == "null":
        return ""
    return parent


def hierarchy_entries(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized ancestor hierarchy entries (nearest parent first)."""
    parent_id = hierarchy_parent_id(metadata)
    if not parent_id:
        return []
    return [{"node_id": parent_id}]


def resolve_hierarchy_chain(
    reader: StandardsReader,
    node_id: str,
    *,
    _visited: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return full ancestor chain by following ``hierarchy.parent`` (nearest first)."""
    _visited = _visited or set()
    if node_id in _visited:
        return []
    _visited.add(node_id)

    try:
        record = reader.load(node_id)
    except FileNotFoundError:
        return []

    chain = list(hierarchy_entries(record.metadata))
    if not chain:
        return chain

    parent_id = str(chain[0].get("node_id", "")).strip()
    if not parent_id:
        return chain

    parent_chain = resolve_hierarchy_chain(reader, parent_id, _visited=_visited)
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in chain + parent_chain:
        ref = str(item.get("node_id", "")).strip()
        if not ref or ref in seen:
            continue
        seen.add(ref)
        merged.append(item)
        if not item.get("title"):
            try:
                parent_record = reader.load(ref)
            except FileNotFoundError:
                continue
            title = str(parent_record.metadata.get("title", "")).strip()
            if title:
                item["title"] = title
    return merged
