"""Suggest related follow-up workflows after a task completes."""

from __future__ import annotations

from typing import Any

from ai.agents.base import BaseAgent
from ai.client import MissingAPIKeyError

_FALLBACK_SUGGESTIONS: dict[str, list[dict[str, str]]] = {
    "pipe_wall_thickness_design": [
        {
            "id": "flange_rating_check",
            "title": "Flange rating verification",
            "description": "Verify flange class against design pressure and temperature for the same line.",
        },
        {
            "id": "corrosion_allowance_review",
            "title": "Corrosion allowance review",
            "description": "Re-evaluate corrosion allowance and remaining life for the calculated pipe.",
        },
        {
            "id": "pressure_test_planning",
            "title": "Hydrotest pressure planning",
            "description": "Determine hydrostatic test pressure and hold criteria for the completed design.",
        },
    ],
}

_DEFAULT_FALLBACK: list[dict[str, str]] = [
    {
        "id": "design_assumption_review",
        "title": "Review design assumptions",
        "description": "Walk through key inputs and assumptions from the completed calculation.",
    },
    {
        "id": "related_code_check",
        "title": "Related code compliance check",
        "description": "Check adjacent code requirements that may apply to this design topic.",
    },
]


def fallback_suggestions(workflow_id: str) -> list[dict[str, str]]:
    if workflow_id in _FALLBACK_SUGGESTIONS:
        return [dict(item) for item in _FALLBACK_SUGGESTIONS[workflow_id]]
    return [dict(item) for item in _DEFAULT_FALLBACK]


def normalize_suggestions(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        suggestion_id = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        if not suggestion_id or not title or not description:
            continue
        normalized.append(
            {
                "id": suggestion_id,
                "title": title,
                "description": description,
            }
        )
    return normalized[:4]


class TaskContinuationAgent(BaseAgent):
    prompt_file = "task_continuation.md"

    def suggest(
        self,
        *,
        context_brief: str = "",
        workflow_id: str = "",
    ) -> list[dict[str, str]]:
        try:
            _ = self.client
        except MissingAPIKeyError:
            return fallback_suggestions(workflow_id)

        user_prompt = (
            "The engineering task is complete. Suggest follow-up workflows.\n\n"
            f"Workflow id: {workflow_id or 'unknown'}\n\n"
            f"{context_brief.strip() or 'No additional context.'}"
        )
        try:
            payload = self.complete_json(user_prompt)
        except Exception:
            return fallback_suggestions(workflow_id)

        suggestions = normalize_suggestions(payload.get("suggestions"))
        if suggestions:
            return suggestions
        return fallback_suggestions(workflow_id)
