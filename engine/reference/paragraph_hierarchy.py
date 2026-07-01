"""Paragraph ancestor hierarchy helpers for standards section nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.reference.graph_edge_schema import edge_target, iter_stored_edges

if TYPE_CHECKING:
    from engine.reference.standards_reader import StandardsReader


def paragraph_reference(metadata: dict[str, Any]) -> str:
    """Return the standards paragraph id for display and provenance."""
    return str(metadata.get("paragraph") or metadata.get("id") or "").strip()


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


def hierarchy_entries(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized ancestor hierarchy entries (nearest parent first)."""
    entries: list[dict[str, Any]] = []
    for item in iter_stored_edges(metadata):
        if str(item.get("type") or "") != "parent":
            continue
        node_id = edge_target(item)
        if not node_id:
            continue
        entry: dict[str, Any] = {"node_id": node_id}
        title = str(item.get("title", "")).strip()
        if title:
            entry["title"] = title
        entries.append(entry)
    return entries


def resolve_hierarchy_chain(
    reader: StandardsReader,
    node_id: str,
    *,
    _visited: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return full ancestor chain by following ``parent`` edges (nearest first)."""
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
