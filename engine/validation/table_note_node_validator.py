"""Validate table-note knowledge nodes against the template."""

from __future__ import annotations

import re
from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.validation.node_revision_metadata import validate_revision_metadata

_TABLE_NOTE_ID_RE = re.compile(r"^(?P<table_id>.+)-note-(?P<note_code>[0-9]+[a-z]?)$")

TABLE_NOTE_PARENT_EDGE_TYPE = "note_for_table"
LOOKUP_HAS_TABLE_NOTE_EDGE_TYPE = "has_table_note"
TABLE_NOTE_REFERENCE_EDGE_TYPE = "related_to"

_FORBIDDEN_FIELDS = frozenset(
    {
        "table_id",
        "value",
        "user_input",
        "runtime_value",
        "fact_value",
        "formula",
    }
)


def parent_table_id_from_note_id(node_id: str) -> str:
    match = _TABLE_NOTE_ID_RE.match(node_id.strip())
    if not match:
        return ""
    return str(match.group("table_id") or "").strip()


def is_table_note_id(node_id: str) -> bool:
    return bool(_TABLE_NOTE_ID_RE.match(node_id.strip()))


def _table_note_text(meta: dict[str, Any]) -> str:
    raw = meta.get("text")
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return str(raw.get("original") or "").strip()
    return ""


def _edge_targets(meta: dict[str, Any], edge_type: str) -> list[str]:
    targets: list[str] = []
    for item in meta.get("edges") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").strip() == edge_type:
            target = str(item.get("target") or "").strip()
            if target:
                targets.append(target)
    return targets


def validate_table_note_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "table_note":
        issues.append("type must be 'table_note'")

    node_id = str(meta.get("id") or "").strip()
    parent_table_id = parent_table_id_from_note_id(node_id)
    if not node_id:
        issues.append("missing id")
    elif not parent_table_id:
        issues.append(
            "id must match {table_id}-note-{note_code} "
            "(e.g. asme-b313-table-302-3-3-1-note-1)"
        )

    note_code = str(meta.get("note_code") or "").strip()
    if not note_code:
        issues.append("missing note_code")
    elif node_id and not node_id.endswith(f"-note-{note_code}"):
        issues.append("id suffix must match note_code")

    if not str(meta.get("title") or "").strip():
        issues.append("missing title")
    if not _table_note_text(meta):
        issues.append("missing text")

    parent_targets = _edge_targets(meta, TABLE_NOTE_PARENT_EDGE_TYPE)
    if not parent_targets:
        issues.append(
            f"table_note requires {TABLE_NOTE_PARENT_EDGE_TYPE} edge to parent table"
        )
    elif parent_table_id and parent_table_id not in parent_targets:
        issues.append(
            f"table_note requires {TABLE_NOTE_PARENT_EDGE_TYPE} edge to parent table "
            f"{parent_table_id}"
        )
    if parent_table_id and parent_table_id in _edge_targets(meta, TABLE_NOTE_REFERENCE_EDGE_TYPE):
        issues.append(
            f"use {TABLE_NOTE_PARENT_EDGE_TYPE} for parent table; "
            f"{TABLE_NOTE_REFERENCE_EDGE_TYPE} is for other cited nodes only"
        )

    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")

    issues.extend(validate_revision_metadata(meta))
    issues.extend(validate_no_links_metadata(meta))

    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="table_note", allow_legacy=False)
            )
    return issues
