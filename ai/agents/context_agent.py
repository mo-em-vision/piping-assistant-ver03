"""Conversation continuity and context-switch detection."""

from __future__ import annotations

from models.agent import AgentAction, AgentContext, ContextResult, OverrideConfirmation

from ai.agents._constants import CONTEXT_KEYWORDS
from ai.agents.base import BaseAgent
from ai.prompts_loader import load_prompt


class ContextAgent(BaseAgent):
    prompt_file = "intent_detection.md"

    def evaluate(
        self,
        message: str,
        *,
        context: AgentContext | None = None,
    ) -> ContextResult:
        active_task_id = context.active_task_id if context else None

        if self._looks_unrelated(message):
            return ContextResult(
                context_switch_detected=True,
                preserve_task=True,
                active_task_id=active_task_id,
                message=(
                    "Your message appears unrelated to the active engineering task. "
                    "Would you like to continue the current analysis or start something new?"
                ),
                action=AgentAction.CONTEXT_SWITCH,
            )

        if active_task_id:
            return ContextResult(
                context_switch_detected=False,
                preserve_task=True,
                active_task_id=active_task_id,
                message="",
                action=AgentAction.GENERAL_RESPONSE,
            )

        if self._client is not None:
            try:
                return self._evaluate_with_llm(message, context)
            except Exception:
                pass

        return ContextResult(
            context_switch_detected=False,
            preserve_task=True,
            active_task_id=active_task_id,
            message="",
            action=AgentAction.GENERAL_RESPONSE,
        )

    @staticmethod
    def confirm_override(
        violated_rule: str,
        *,
        user_decision: str = "pending",
        reason: str = "",
    ) -> OverrideConfirmation:
        return OverrideConfirmation(
            violated_rule=violated_rule,
            user_decision=user_decision,
            reason=reason,
        )

    @staticmethod
    def _looks_unrelated(message: str) -> bool:
        return any(pattern.search(message) for pattern in CONTEXT_KEYWORDS)

    def _evaluate_with_llm(self, message: str, context: AgentContext | None) -> ContextResult:
        payload = self.complete_json(
            f"Message:\n{message}\n\nContext:\n{self.format_context(context.__dict__ if context else None)}",
            extra_system=load_prompt("intent_detection.md"),
        )
        unrelated = payload.get("category") == "unrelated" or not payload.get(
            "is_engineering_request", True
        )
        if unrelated and context and context.active_task_id:
            return ContextResult(
                context_switch_detected=True,
                preserve_task=True,
                active_task_id=context.active_task_id,
                message=(
                    "This may be unrelated to your active engineering task. "
                    "Continue the current task or switch?"
                ),
                action=AgentAction.CONTEXT_SWITCH,
            )
        return ContextResult(
            context_switch_detected=False,
            preserve_task=True,
            active_task_id=context.active_task_id if context else None,
            action=AgentAction.GENERAL_RESPONSE,
        )
