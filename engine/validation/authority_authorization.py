"""Authorization rules for equation and validation_rule nodes."""

from __future__ import annotations

from typing import Any


def _has_edge(meta: dict[str, Any], edge_type: str) -> bool:
    for item in meta.get("edges") or []:
        if isinstance(item, dict) and str(item.get("type") or "") == edge_type:
            return True
    return False


def validate_authority_authorization(meta: dict[str, Any], *, node_type: str) -> list[str]:
    """Require governing paragraphs in authority.authorized_by; forbid authorized_by edges."""
    issues: list[str] = []
    authority = meta.get("authority")
    if not isinstance(authority, dict):
        issues.append("authority block required")
        return issues
    authorized = authority.get("authorized_by") or []
    if not authorized:
        issues.append("authority.authorized_by required")
    elif not isinstance(authorized, list) or not all(
        isinstance(item, str) and item.strip() for item in authorized
    ):
        issues.append("authority.authorized_by must be a non-empty list of paragraph ids")
    if authority.get("authority_context_required") is None:
        issues.append("authority.authority_context_required required")
    if _has_edge(meta, "authorized_by"):
        issues.append(
            f"{node_type} must not declare authorized_by edges; "
            "list governing paragraphs in authority.authorized_by"
        )
    return issues
