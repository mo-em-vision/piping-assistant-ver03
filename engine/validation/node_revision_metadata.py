"""Shared revision metadata rules for knowledge nodes."""

from __future__ import annotations

from typing import Any

DEFAULT_LAST_REVISION = "2026-07-04"
DEFAULT_EDITED_BY = "admin"


def ensure_revision_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Return metadata with required revision fields (mutates a copy)."""
    out = dict(meta)
    node_metadata = out.get("metadata")
    if not isinstance(node_metadata, dict):
        node_metadata = {}
    else:
        node_metadata = dict(node_metadata)
    node_metadata.setdefault("last_revision", DEFAULT_LAST_REVISION)
    node_metadata.setdefault("edited_by", DEFAULT_EDITED_BY)
    out["metadata"] = node_metadata
    return out


def stamp_revision_metadata(
    meta: dict[str, Any],
    *,
    edited_by: str = DEFAULT_EDITED_BY,
    last_revision: str | None = None,
) -> dict[str, Any]:
    """Set revision fields on create/edit (returns a copy)."""
    from datetime import date

    out = dict(meta)
    node_metadata = out.get("metadata")
    if not isinstance(node_metadata, dict):
        node_metadata = {}
    else:
        node_metadata = dict(node_metadata)
    node_metadata["last_revision"] = last_revision or date.today().isoformat()
    node_metadata["edited_by"] = edited_by
    out["metadata"] = node_metadata
    return out


def validate_revision_metadata(meta: dict[str, Any]) -> list[str]:
    """Return validation issues for missing revision metadata."""
    issues: list[str] = []
    node_metadata = meta.get("metadata")
    if not isinstance(node_metadata, dict):
        issues.append("metadata block required")
        return issues
    if not node_metadata.get("last_revision"):
        issues.append("metadata.last_revision required")
    if not node_metadata.get("edited_by"):
        issues.append("metadata.edited_by required")
    return issues
