"""Workflow display metadata for task titles and center-panel headers."""

from __future__ import annotations

from typing import Any

from engine.planner.workflow_goal_metadata import (
    workflow_display_description_from_node,
    workflow_display_title_from_node,
)
from engine.reference.standards_reader import StandardsReader


def workflow_display_meta(
    workflow_id: str,
    catalog_meta: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, str]:
    """Resolve workflow title/description from workflow node when a reader is available."""
    base = dict(catalog_meta or {})
    node_title = ""
    node_description = ""
    if reader is not None and workflow_id:
        node_title = workflow_display_title_from_node(reader, workflow_id)
        node_description = workflow_display_description_from_node(reader, workflow_id)

    display_title = node_title or str(
        base.get("display_title") or base.get("name") or workflow_id.replace("_", " ").title()
    ).strip()
    subtitle = node_description or str(base.get("subtitle") or base.get("description") or "").strip()
    standard_ref = str(base.get("standard_ref") or "").strip()
    return {
        "workflow_id": workflow_id,
        "display_title": display_title,
        "subtitle": subtitle,
        "standard_ref": standard_ref,
    }


def task_display_title(
    workflow_id: str,
    catalog_meta: dict[str, Any] | None = None,
    *,
    reader: StandardsReader | None = None,
) -> str:
    meta = catalog_meta
    if meta is None:
        try:
            from api.serializers import _workflow_meta

            meta = _workflow_meta(workflow_id, reader=reader)
        except Exception:
            meta = {}
    return workflow_display_meta(workflow_id, meta, reader=reader)["display_title"]
