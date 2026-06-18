"""Intent classification — wraps deterministic router and enriches with LLM fallback."""

from __future__ import annotations

from typing import Any

from engine.router import PIPE_WALL_THICKNESS_DESIGN, route
from models.agent import AgentAction, AgentContext, IntentResult

from ai.agents._constants import (
    PIPE_WALL_THICKNESS_ROOT,
    detect_missing_context,
)
from ai.agents.base import BaseAgent


class IntentAgent(BaseAgent):
    prompt_file = "intent_agent.md"

    def analyze(self, request: str, context: AgentContext | None = None) -> IntentResult:
        if context and context.active_task_id and context.workflow:
            return self._from_workflow_continuation(request, context)

        workflow = route(request)
        if workflow == PIPE_WALL_THICKNESS_DESIGN:
            return self._from_router_match(request, workflow)

        try:
            return self._analyze_with_llm(request, context)
        except Exception:
            return IntentResult(
                intent=None,
                domain=None,
                confidence=0.0,
                action=AgentAction.CLARIFY,
                message=(
                    "I could not classify this engineering request. "
                    "Please describe whether you need pipe wall thickness design or another analysis."
                ),
            )

    def _from_workflow_continuation(
        self,
        request: str,
        context: AgentContext,
    ) -> IntentResult:
        workflow = context.workflow or PIPE_WALL_THICKNESS_DESIGN
        missing = list(context.missing_inputs) if context.missing_inputs else detect_missing_context(request)
        return IntentResult(
            intent=workflow,
            domain="piping",
            possible_standards=["ASME B31.3"],
            root_nodes=[PIPE_WALL_THICKNESS_ROOT],
            missing_context=missing,
            confidence=0.95,
            workflow=workflow,
            action=AgentAction.PROPOSE_PATH,
        )

    def _from_router_match(self, request: str, workflow: str) -> IntentResult:
        return IntentResult(
            intent=workflow,
            domain="piping",
            possible_standards=["ASME B31.3"],
            root_nodes=[PIPE_WALL_THICKNESS_ROOT],
            missing_context=detect_missing_context(request),
            confidence=0.95,
            workflow=workflow,
            action=AgentAction.PROPOSE_PATH,
        )

    def _analyze_with_llm(self, request: str, context: AgentContext | None) -> IntentResult:
        payload = self.complete_json(
            f"User request:\n{request}\n\nContext:\n{self.format_context(context.__dict__ if context else None)}",
            extra_system='If unrelated to engineering, set intent to null and action to "clarify".',
        )
        return self._parse_intent(payload)

    @staticmethod
    def _parse_intent(payload: dict[str, Any]) -> IntentResult:
        confidence = float(payload.get("confidence", 0.0))
        action_value = payload.get("action", "clarify")
        action = AgentAction(action_value) if action_value in AgentAction._value2member_map_ else AgentAction.CLARIFY
        if confidence < 0.6 and action != AgentAction.CLARIFY:
            action = AgentAction.CLARIFY

        return IntentResult(
            intent=payload.get("intent"),
            domain=payload.get("domain"),
            possible_standards=list(payload.get("possible_standards", [])),
            root_nodes=list(payload.get("root_nodes", [])),
            missing_context=list(payload.get("missing_context", [])),
            confidence=confidence,
            workflow=payload.get("intent"),
            action=action,
            message=payload.get("message"),
        )
