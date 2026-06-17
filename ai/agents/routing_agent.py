"""Multi-standard routing when multiple design bases may apply."""

from __future__ import annotations

import re
from typing import Any

from models.agent import AgentAction, RoutingResult, StandardOption

from ai.agents._constants import INSPECTION_KEYWORDS, PIPE_WALL_THICKNESS_DESIGN
from ai.agents.base import BaseAgent
from engine.router import route


class RoutingAgent(BaseAgent):
    prompt_file = "routing_agent.md"

    def route(self, request: str) -> RoutingResult:
        deterministic = self._deterministic_route(request)
        if deterministic is not None:
            return deterministic

        if self._client is not None:
            try:
                return self._route_with_llm(request)
            except Exception:
                pass

        return RoutingResult(
            options=[StandardOption("ASME B31.3", "Process piping design and analysis")],
            action=AgentAction.ROUTE_STANDARD,
            message="Defaulting to ASME B31.3 for piping analysis.",
            selected_standard="ASME B31.3",
        )

    def _deterministic_route(self, request: str) -> RoutingResult | None:
        if route(request) == PIPE_WALL_THICKNESS_DESIGN:
            return RoutingResult(
                options=[StandardOption("ASME B31.3", "Process piping — wall thickness design")],
                action=AgentAction.ROUTE_STANDARD,
                selected_standard="ASME B31.3",
                message="ASME B31.3 applies to pipe wall thickness design.",
            )

        if any(pattern.search(request) for pattern in INSPECTION_KEYWORDS):
            return RoutingResult(
                options=[
                    StandardOption("ASME B31.3", "Process piping design and analysis"),
                    StandardOption("API 570", "Piping inspection"),
                ],
                action=AgentAction.ROUTE_STANDARD,
                message="Multiple standards may apply. Please select the design basis.",
            )

        return None

    def _route_with_llm(self, request: str) -> RoutingResult:
        payload = self.complete_json(f"User request:\n{request}")
        options = [
            StandardOption(
                standard=str(item.get("standard", "")),
                description=str(item.get("description", "")),
            )
            for item in payload.get("options", [])
        ]
        return RoutingResult(
            options=options,
            action=AgentAction.ROUTE_STANDARD,
            message=payload.get("message"),
            selected_standard=payload.get("selected_standard"),
        )

    def record_alternative(
        self,
        selected: str,
        alternative: str,
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return {
            "selected": selected,
            "alternative": alternative,
            "reason": reason,
        }
