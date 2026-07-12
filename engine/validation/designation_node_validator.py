"""Validate designation knowledge nodes against audits/contracts/nodes/designation.md."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.validation.node_revision_metadata import validate_revision_metadata

_FORBIDDEN_FIELDS = frozenset(
    {
        "value",
        "user_input",
        "runtime_value",
        "fact_value",
        "dimension",
        "unit",
        "resolution",
        "execution_id",
    }
)


def validate_designation_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "designation":
        issues.append("type must be 'designation'")
    if not str(meta.get("id") or "").strip():
        issues.append("missing id")
    if not str(meta.get("name") or "").strip():
        issues.append("missing name")
    if not str(meta.get("symbol") or "").strip():
        issues.append("missing symbol")

    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")

    issues.extend(validate_revision_metadata(meta))
    issues.extend(validate_no_links_metadata(meta))

    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="designation", allow_legacy=False)
            )
    return issues
