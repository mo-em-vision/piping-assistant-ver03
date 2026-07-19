"""Validate lookup knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.validation.binding_block_consistency import validate_binding_block_consistency
from engine.validation.node_revision_metadata import validate_revision_metadata
from engine.reference.table_metadata import table_reference
from engine.validation.table_note_node_validator import (
    LOOKUP_HAS_TABLE_NOTE_EDGE_TYPE,
    TABLE_NOTE_REFERENCE_EDGE_TYPE,
    parent_table_id_from_note_id,
)

_FORBIDDEN_FIELDS = frozenset(
    {
        "runtime_value",
        "fact_value",
        "user_input",
        "execution_id",
        "task_id",
        "calculation_result",
        "selected_for_execution",
        "active_in_context",
    }
)


def validate_lookup_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "lookup":
        issues.append("type must be 'lookup'")
    if not meta.get("key") and not meta.get("title"):
        issues.append("missing key or title")
    if not meta.get("name") and not meta.get("title"):
        issues.append("missing name or title")
    if not meta.get("description") and not meta.get("title"):
        issues.append("missing description or title")

    if not str(meta.get("table_number") or "").strip():
        source = meta.get("source")
        nested = ""
        if isinstance(source, dict):
            nested = str(source.get("table_number") or "").strip()
        if not nested and not table_reference(meta):
            issues.append("missing table_number")

    lookup_block = meta.get("lookup") or {}
    has_table = bool(
        meta.get("table_id")
        or (isinstance(lookup_block, dict) and lookup_block.get("table"))
        or _has_edge(meta, "reads_table")
    )
    if not has_table:
        issues.append("lookup requires table_id, lookup.table, or reads_table edge")

    has_output = bool(
        meta.get("output_param")
        or meta.get("returns")
        or _has_edge(meta, "returns_parameter")
        or _has_edge(meta, "calculates_parameter")
    )
    if not has_output:
        issues.append("lookup requires output_param, returns, or returns_parameter edge")

    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")

    issues.extend(validate_revision_metadata(meta))
    issues.extend(validate_no_links_metadata(meta))

    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            edge_type = str(item.get("type") or "")
            if edge_type == "calculates_parameter":
                issues.append("lookup must use returns_parameter, not calculates_parameter")
            issues.extend(
                validate_edge_item(item, source_node_type="lookup", allow_legacy=False)
            )

    issues.extend(_validate_table_note_edges(meta))
    issues.extend(_validate_lookup_node_policy_fields(meta))
    from engine.validation.lookup_rule_validator import validate_lookup_config

    lookup_cfg = meta.get("lookup") if isinstance(meta.get("lookup"), dict) else {}
    if lookup_cfg:
        issues.extend(validate_lookup_config(meta))
    issues.extend(validate_binding_block_consistency(meta))
    return issues


def _table_note_ids(meta: dict[str, Any]) -> list[str]:
    note_ids: list[str] = []
    for item in meta.get("notes") or []:
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id") or "").strip()
        if node_id:
            note_ids.append(node_id)
    return note_ids


def _edge_targets(meta: dict[str, Any], edge_type: str) -> set[str]:
    targets: set[str] = set()
    for item in meta.get("edges") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").strip() == edge_type:
            target = str(item.get("target") or "").strip()
            if target:
                targets.add(target)
    return targets


def _validate_table_note_edges(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    note_ids = _table_note_ids(meta)
    if not note_ids:
        return issues

    has_table_note = _edge_targets(meta, LOOKUP_HAS_TABLE_NOTE_EDGE_TYPE)
    related_to = _edge_targets(meta, TABLE_NOTE_REFERENCE_EDGE_TYPE)
    lookup_id = str(meta.get("id") or "").strip()
    for note_id in note_ids:
        if note_id not in has_table_note:
            issues.append(
                f"missing {LOOKUP_HAS_TABLE_NOTE_EDGE_TYPE} edge to table note: {note_id}"
            )
        if note_id in related_to:
            issues.append(
                f"use {LOOKUP_HAS_TABLE_NOTE_EDGE_TYPE} for table note {note_id}; "
                f"{TABLE_NOTE_REFERENCE_EDGE_TYPE} is for other cited nodes only"
            )
        expected_parent = parent_table_id_from_note_id(note_id)
        if expected_parent and lookup_id and expected_parent != lookup_id:
            issues.append(
                f"table note {note_id} id prefix does not match lookup id {lookup_id}"
            )
    return issues


def _validate_lookup_node_policy_fields(meta: dict[str, Any]) -> list[str]:
    """Reject resolution policy fields that belong on table definitions."""
    issues: list[str] = []
    forbidden_top_level = (
        "lookup_rules",
        "row_resolution",
        "interpolation",
        "interpolate_columns",
    )
    for field in forbidden_top_level:
        if field in meta:
            issues.append(
                f"lookup node must not contain {field!r}; "
                "author on the table definition YAML"
            )
    lookup_cfg = meta.get("lookup")
    if isinstance(lookup_cfg, dict):
        for field in ("interpolation", "row_resolution", "interpolate_columns"):
            if field in lookup_cfg:
                issues.append(f"lookup block must not contain {field!r}")
    return issues


def _has_edge(meta: dict[str, Any], edge_type: str) -> bool:
    for item in meta.get("edges") or []:
        if isinstance(item, dict) and str(item.get("type") or "") == edge_type:
            return True
    return False
