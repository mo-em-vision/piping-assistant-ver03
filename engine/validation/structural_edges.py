"""Reject parent/child structural edges where hierarchy metadata is required."""

from __future__ import annotations

from typing import Any

FORBIDDEN_STRUCTURAL_EDGE_TYPES = frozenset({"parent", "child", "children", "next", "previous"})


def validate_no_structural_edges(meta: dict[str, Any], *, node_type: str) -> list[str]:
    """Return issues when edges use hierarchy edge types instead of metadata."""
    issues: list[str] = []
    for item in meta.get("edges") or []:
        if not isinstance(item, dict):
            continue
        edge_type = str(item.get("type") or "").strip()
        if edge_type not in FORBIDDEN_STRUCTURAL_EDGE_TYPES:
            continue
        if node_type == "paragraph":
            hint = "use hierarchy metadata instead"
        else:
            hint = "use hierarchy metadata (paragraphs) or authority.authorized_by (equations, validation_rule)"
        issues.append(f"{node_type} nodes must not use structural edge type: {edge_type}; {hint}")
    return issues
