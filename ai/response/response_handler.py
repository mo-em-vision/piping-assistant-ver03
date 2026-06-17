"""Format structured agent outputs into human-readable responses."""

from __future__ import annotations

from models.agent import (
    AgentAction,
    ContextResult,
    InputAgentResult,
    IntentResult,
    PlannerResult,
    RoutingResult,
    SynthesisResult,
)


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

    def format_input_requests(self, result: InputAgentResult) -> str:
        if not result.requests:
            return "All required inputs are available."
        lines = ["Required inputs:"]
        for request in result.requests:
            symbol = f" ({request.symbol})" if request.symbol else ""
            lines.append(f"- {request.input_id}{symbol}: {request.reason}")
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
