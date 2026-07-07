"""Validate lookup knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.validation.node_revision_metadata import validate_revision_metadata
from engine.reference.table_metadata import table_reference

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
    return issues


def _has_edge(meta: dict[str, Any], edge_type: str) -> bool:
    for item in meta.get("edges") or []:
        if isinstance(item, dict) and str(item.get("type") or "") == edge_type:
            return True
    return False
