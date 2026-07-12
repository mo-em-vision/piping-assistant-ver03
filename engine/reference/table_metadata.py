"""Table node citation helpers for standards lookup nodes."""

from __future__ import annotations

import re
from typing import Any

from engine.reference.graph_compile import LEGACY_NODE_ID_ALIASES

_TABLE_NUMBER_FROM_TITLE = re.compile(r"^Table\s+(.+?)(?:\s+—|\s+-|$)", re.IGNORECASE)


def table_reference(metadata: dict[str, Any]) -> str:
    """Return the standards table number for display and provenance."""
    explicit = str(metadata.get("table_number") or "").strip()
    if explicit:
        return explicit

    source = metadata.get("source")
    if isinstance(source, dict):
        nested = str(source.get("table_number") or "").strip()
        if nested:
            return nested

    title = str(metadata.get("title") or metadata.get("name") or "").strip()
    match = _TABLE_NUMBER_FROM_TITLE.match(title)
    if match:
        return match.group(1).strip()

    node_id = str(metadata.get("id") or "").strip()
    if node_id.startswith("asme-b313-table-"):
        suffix = node_id.removeprefix("asme-b313-table-")
        return _table_number_from_id_suffix(suffix)

    return ""


def table_paragraph_reference(metadata: dict[str, Any]) -> str:
    """Table lookup nodes cite by table number only — no paragraph suffix in display."""
    _ = metadata
    return ""


def resolve_table_db_id(
    reader: Any,
    metadata: dict[str, Any] | None,
    *,
    table_ref: str = "",
) -> str:
    """Return a table id accepted by standards table APIs (tables.db primary key)."""
    from engine.reference.standards_tables import StandardsTablesDatabase

    tables_db = getattr(reader, "tables_database", None) or getattr(reader, "_tables_db", None)
    if not isinstance(tables_db, StandardsTablesDatabase):
        return table_ref or str((metadata or {}).get("id") or "").strip()

    source = (metadata or {}).get("source")
    if isinstance(source, dict):
        db_table_id = str(source.get("table_id") or "").strip()
        if db_table_id and tables_db.resolve_table_id(db_table_id):
            return db_table_id

    for candidate in (
        table_ref,
        str((metadata or {}).get("id") or "").strip(),
    ):
        if candidate:
            resolved = tables_db.resolve_table_id(candidate)
            if resolved:
                return resolved
    return table_ref or str((metadata or {}).get("id") or "").strip()


def _table_number_from_id_suffix(suffix: str) -> str:
    text = suffix.strip()
    if not text:
        return ""
    if re.match(r"^[A-Za-z]", text):
        return text
    parts = text.split("-")
    if len(parts) == 1:
        return text
    if parts[-1].isdigit():
        return f"{'.'.join(parts[:-1])}-{parts[-1]}"
    return ".".join(parts)


def resolve_lookup_node_id(reader: Any, table_ref: str) -> str | None:
    """Resolve a standards lookup node id from a table db ref or alias."""
    from engine.reference.standards_tables import StandardsTablesDatabase

    ref = str(table_ref or "").strip()
    if not ref:
        return None

    if "/" in ref:
        ref = ref.rsplit("/", 1)[-1]

    alias = LEGACY_NODE_ID_ALIASES.get(ref) or LEGACY_NODE_ID_ALIASES.get(ref.lower())
    if alias:
        return alias

    tables_db = getattr(reader, "_tables_db", None)
    if isinstance(tables_db, StandardsTablesDatabase):
        data = tables_db.get_table(ref)
        if isinstance(data, dict):
            source_node = str(data.get("source_node") or "").strip()
            if source_node:
                return LEGACY_NODE_ID_ALIASES.get(source_node, source_node)

    if ref.startswith("asme-b313-table-"):
        return ref

    normalized = ref.lower().replace("asme_b31.3_", "").replace("asme_b31.3/", "")
    if normalized.startswith("table_"):
        normalized = normalized.removeprefix("table_")
    candidate = f"asme-b313-table-{normalized.replace('_', '-')}"
    try:
        reader.load(candidate)
        return candidate
    except FileNotFoundError:
        return None


def table_citation_labels(
    reader: Any,
    table_ref: str,
) -> tuple[str | None, str | None]:
    """Return (table_number, paragraph_number) for a table lookup reference."""
    node_id = resolve_lookup_node_id(reader, table_ref)
    if not node_id:
        return None, None
    try:
        record = reader.load(node_id)
    except FileNotFoundError:
        return None, None
    metadata = record.metadata
    table_number = table_reference(metadata) or None
    return table_number, None


def format_table_citation(
    *,
    standard_label: str,
    table_number: str | None,
    paragraph_number: str | None = None,
) -> str:
    """Build a user-facing table citation label (table number only)."""
    _ = paragraph_number
    if table_number:
        return f"{standard_label} Table {table_number}"
    return standard_label
