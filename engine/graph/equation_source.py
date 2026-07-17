"""Graph provenance resolution for equation nodes."""

from __future__ import annotations

from engine.reference.standards_reader import StandardsReader


def source_node_id_for_equation(reader: StandardsReader, equation_node_id: str) -> str:
    """Resolve the paragraph/definition node that owns an equation for display provenance."""
    try:
        record = reader.load(equation_node_id)
    except FileNotFoundError:
        return equation_node_id

    metadata = record.metadata
    authority = metadata.get("authority") or {}
    authorized = authority.get("authorized_by") or []
    if authorized:
        candidate = str(authorized[0]).strip()
        if candidate:
            return candidate

    paragraph_number = str(metadata.get("paragraph_number") or "").strip()
    if paragraph_number:
        return paragraph_number

    return equation_node_id
