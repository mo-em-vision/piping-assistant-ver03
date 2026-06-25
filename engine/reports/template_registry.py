"""Map engineering workflows to report templates."""

from __future__ import annotations

PIPE_WALL_THICKNESS_WORKFLOW = "pipe_wall_thickness_design"

_WORKFLOW_TEMPLATES: dict[str, str] = {
    PIPE_WALL_THICKNESS_WORKFLOW: "pipe_wall_thickness_design_report.md",
}

DEFAULT_TEMPLATE = "generic_task_report.md"


def resolve_template_name(workflow: str) -> str:
    normalized = (workflow or "").strip().lower()
    if normalized in _WORKFLOW_TEMPLATES:
        return _WORKFLOW_TEMPLATES[normalized]
    if PIPE_WALL_THICKNESS_WORKFLOW in normalized.replace("-", "_"):
        return _WORKFLOW_TEMPLATES[PIPE_WALL_THICKNESS_WORKFLOW]
    return DEFAULT_TEMPLATE
