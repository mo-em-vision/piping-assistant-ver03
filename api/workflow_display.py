"""Workflow display metadata for task titles and center-panel headers."""

from __future__ import annotations

from typing import Any


def workflow_display_meta(workflow_id: str, catalog_meta: dict[str, Any] | None = None) -> dict[str, str]:
    """Merge catalog metadata with display overrides; safe for canonical and API layers."""
    base = dict(catalog_meta or {})
    display_title = str(
        base.get("display_title") or base.get("name") or workflow_id.replace("_", " ").title()
    ).strip()
    subtitle = str(base.get("subtitle") or base.get("description") or "").strip()
    standard_ref = str(base.get("standard_ref") or "").strip()
    return {
        "workflow_id": workflow_id,
        "display_title": display_title,
        "subtitle": subtitle,
        "standard_ref": standard_ref,
    }


def task_display_title(workflow_id: str, catalog_meta: dict[str, Any] | None = None) -> str:
    meta = catalog_meta
    if meta is None:
        try:
            from api.serializers import _workflow_meta

            meta = _workflow_meta(workflow_id)
        except Exception:
            meta = {}
    return workflow_display_meta(workflow_id, meta)["display_title"]
