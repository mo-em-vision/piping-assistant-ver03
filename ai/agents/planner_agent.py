"""Graph navigation planning from identified intent."""

from __future__ import annotations

from typing import Any

from models.agent import AgentAction, IntentResult, PlannerResult

from ai.agents._constants import PIPE_WALL_THICKNESS_DESIGN, PIPE_WALL_THICKNESS_ROOT
from ai.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    prompt_file = "planner_agent.md"

    _DEFAULT_PRIORITIES: dict[str, list[str]] = {
        PIPE_WALL_THICKNESS_DESIGN: [
            "material stress evaluation",
            "pressure design / wall thickness",
            "thin-wall applicability check",
        ],
    }

    def plan(self, intent: IntentResult) -> PlannerResult:
        if intent.intent == PIPE_WALL_THICKNESS_DESIGN:
            return PlannerResult(
                priorities=self._DEFAULT_PRIORITIES[PIPE_WALL_THICKNESS_DESIGN],
                root_nodes=intent.root_nodes or [PIPE_WALL_THICKNESS_ROOT],
                confidence=max(intent.confidence, 0.9),
                action=AgentAction.PROPOSE_PATH,
            )

        if self._client is not None:
            try:
                return self._plan_with_llm(intent)
            except Exception:
                pass

        return PlannerResult(
            priorities=[],
            root_nodes=intent.root_nodes,
            confidence=0.0,
            action=AgentAction.CLARIFY,
        )

    def _plan_with_llm(self, intent: IntentResult) -> PlannerResult:
        payload = self.complete_json(
            f"Intent result:\n{self.format_context(intent.__dict__)}",
        )
        return PlannerResult(
            priorities=list(payload.get("priorities", [])),
            root_nodes=list(payload.get("root_nodes", intent.root_nodes)),
            confidence=float(payload.get("confidence", 0.0)),
            action=AgentAction.PROPOSE_PATH,
        )
