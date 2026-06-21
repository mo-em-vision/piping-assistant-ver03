"""Format structured agent outputs into human-readable responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from models.agent import (
    AgentAction,
    ContextResult,
    InputAgentResult,
    IntentResult,
    PlannerResult,
    RoutingResult,
    SynthesisResult,
)

from ai.input_extractor import InputRejection

if TYPE_CHECKING:
    from engine.reference.standards_reader import StandardsReader
    from models.planning import NavigationPlan
    from models.task import Task


class ResponseHandler:
    """Converts structured agent payloads into user-facing text."""

    def format_intent(self, result: IntentResult) -> str:
        if result.action == AgentAction.CLARIFY and result.message:
            return result.message

        lines = [
            f"Intent: {result.intent or 'unknown'}",
            f"Domain: {result.domain or 'unknown'}",
        ]
        if result.possible_standards:
            lines.append(f"Standards: {', '.join(result.possible_standards)}")
        if result.root_nodes:
            lines.append(f"Root nodes: {', '.join(result.root_nodes)}")
        if result.missing_context:
            lines.append(f"Missing context: {', '.join(result.missing_context)}")
        return "\n".join(lines)

    def format_planner(self, result: PlannerResult) -> str:
        if not result.priorities:
            return "No execution path proposed."
        numbered = "\n".join(
            f"{index}. {label}" for index, label in enumerate(result.priorities, start=1)
        )
        return f"Proposed execution path:\n{numbered}"

    def format_input_requests(
        self,
        result: InputAgentResult,
        *,
        rejections: list[InputRejection] | None = None,
    ) -> str:
        parts: list[str] = []
        if rejections:
            parts.append(self.format_rejections(rejections))
        if not result.requests:
            parts.append("All required inputs are available.")
            return "\n\n".join(parts) if parts else "All required inputs are available."
        lines = ["Required inputs:"]
        for request in result.requests:
            symbol = f" ({request.symbol})" if request.symbol else ""
            lines.append(f"- {request.input_id}{symbol}: {request.reason}")
        parts.append("\n".join(lines))
        return "\n\n".join(parts)

    def format_formula_parameter_prompt(
        self,
        *,
        reader: StandardsReader,
        task: Task,
        navigation_plan: NavigationPlan | None,
        input_result: InputAgentResult,
        rejections: list[InputRejection] | None = None,
    ) -> str | None:
        from engine.messaging.formula_parameter_prompt import build_formula_parameter_prompt

        prompt = build_formula_parameter_prompt(
            reader=reader,
            task=task,
            navigation_plan=navigation_plan,
            missing_input_ids=input_result.missing_inputs,
        )
        if not prompt:
            return None
        parts: list[str] = []
        if rejections:
            parts.append(self.format_rejections(rejections))
        parts.append(prompt)
        return "\n\n".join(parts)

    def format_step_prompt(
        self,
        *,
        reader: StandardsReader,
        task: Task,
        navigation_plan: NavigationPlan | None,
        input_result: InputAgentResult,
        rejections: list[InputRejection] | None = None,
    ) -> str | None:
        from engine.messaging.step_prompt import build_step_prompt

        prompt = build_step_prompt(
            reader=reader,
            task=task,
            navigation_plan=navigation_plan,
            missing_input_ids=input_result.missing_inputs,
        )
        if not prompt:
            return None
        parts: list[str] = []
        if rejections:
            parts.append(self.format_rejections(rejections))
        parts.append(prompt)
        return "\n\n".join(parts)

    @staticmethod
    def format_rejections(rejections: list[InputRejection]) -> str:
        if not rejections:
            return ""
        lines: list[str] = []
        for rejection in rejections:
            label = rejection.input_id.replace("_", " ")
            lines.append(
                f"{label.title()} `{rejection.raw_value}` is invalid: {rejection.reason}."
            )
        return "\n".join(lines)

    def format_routing(self, result: RoutingResult) -> str:
        if result.message:
            header = result.message
        else:
            header = "Select the applicable standard:"
        options = "\n".join(
            f"- {option.standard}: {option.description}" for option in result.options
        )
        return f"{header}\n{options}"

    def format_context(self, result: ContextResult) -> str:
        return result.message

    def format_synthesis(self, result: SynthesisResult) -> str:
        return result.presentation
