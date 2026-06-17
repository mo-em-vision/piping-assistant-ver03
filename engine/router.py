"""Request classification — maps user text to workflow names.

No workflow execution. No AI calls. When classification returns ``None``,
the caller must delegate to the AI agent layer per ``ai_agent_design.md``.
"""

from __future__ import annotations

import re

PIPE_WALL_THICKNESS_DESIGN = "pipe_wall_thickness_design"

_SUPPORTED_WORKFLOWS: frozenset[str] = frozenset({PIPE_WALL_THICKNESS_DESIGN})

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


class Router:
    """Classifies user requests into workflow names."""

    def route(self, request: str) -> str | None:
        return route(request)

    def supported_workflows(self) -> frozenset[str]:
        return _SUPPORTED_WORKFLOWS
