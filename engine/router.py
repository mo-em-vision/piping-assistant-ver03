"""Request classification — maps user text to workflow names.

No workflow execution. No AI calls. When classification returns ``None``,
the caller must delegate to the AI agent layer per ``ai_agent_design.md``.
"""

from __future__ import annotations

import re

from engine.graph.graph_engine import normalize_root_id

PIPE_WALL_THICKNESS_DESIGN = "pipe_wall_thickness_design"
MAWP_DESIGN = "mawp_design"

_SUPPORTED_WORKFLOWS: frozenset[str] = frozenset({PIPE_WALL_THICKNESS_DESIGN, MAWP_DESIGN})

_MATCH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        PIPE_WALL_THICKNESS_DESIGN,
        re.compile(
            r"\b("
            r"pipe\s+wall\s+thickness(?:\s+design)?|"
            r"wall\s+thickness(?:\s+design)?|"
            r"pipe\s+thickness(?:\s+design)?|"
            r"design\s+pipe\s+thickness|"
            r"calculate\s+pipe\s+thickness|"
            r"pipe\s+thickness\s+design"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        MAWP_DESIGN,
        re.compile(
            r"\b("
            r"mawp|"
            r"maximum\s+allowable\s+working\s+pressure|"
            r"allowable\s+working\s+pressure"
            r")\b",
            re.IGNORECASE,
        ),
    ),
)


def route(request: str) -> str | None:
    """Return a workflow name for a supported request, or ``None`` if unmatched.

    An unmatched request (``None``) should be handled by the AI agent layer
    for intent detection, clarification, or general response — not by this module.
    """
    text = request.strip()
    if not text:
        return None

    for workflow_name, pattern in _MATCH_PATTERNS:
        if pattern.search(text):
            return workflow_name

    return None


def supported_planning_workflows() -> frozenset[str]:
    """Workflow ids that use EngineeringPlan as the navigation authority."""
    return _SUPPORTED_WORKFLOWS


def normalize_planning_workflow_id(workflow_id: str | None) -> str:
    """Map legacy graph workflow ids to canonical planning workflow slugs."""
    if not workflow_id:
        return ""
    text = str(workflow_id).strip()
    if not text:
        return ""
    if text in _SUPPORTED_WORKFLOWS:
        return text
    from engine.graph.workflow_adapters import LEGACY_ROOT_ALIASES

    slug = normalize_root_id(text)
    if slug in _SUPPORTED_WORKFLOWS:
        return slug

    graph_to_canonical = {
        graph_id: canonical
        for canonical, graph_id in LEGACY_ROOT_ALIASES.items()
        if canonical in _SUPPORTED_WORKFLOWS
    }
    for candidate in (text, slug):
        if candidate in graph_to_canonical:
            return graph_to_canonical[candidate]

    for alias_key, graph_id in LEGACY_ROOT_ALIASES.items():
        if alias_key in _SUPPORTED_WORKFLOWS:
            continue
        if text == alias_key or slug == alias_key:
            return graph_to_canonical.get(graph_id, text)

    return text


def is_supported_planning_workflow(workflow_id: str | None) -> bool:
    """Return True when *workflow_id* is a supported EngineeringPlan workflow."""
    normalized = normalize_planning_workflow_id(workflow_id)
    return bool(normalized) and normalized in _SUPPORTED_WORKFLOWS


class Router:
    """Classifies user requests into workflow names."""

    def route(self, request: str) -> str | None:
        return route(request)

    def supported_workflows(self) -> frozenset[str]:
        return _SUPPORTED_WORKFLOWS
