"""Behavioral tests for RoutingAgent and ContextAgent."""

from __future__ import annotations

from ai.agents.context_agent import ContextAgent
from ai.agents.routing_agent import RoutingAgent
from models.agent import AgentAction, AgentContext


def test_routing_agent_offers_multiple_standards_for_inspection() -> None:
    agent = RoutingAgent(client=None)
    result = agent.route("Inspect this pipe for continued service")

    assert len(result.options) >= 2
    standards = {option.standard for option in result.options}
    assert "ASME B31.3" in standards
    assert "API 570" in standards
    assert result.action == AgentAction.ROUTE_STANDARD


def test_context_agent_detects_unrelated_message() -> None:
    agent = ContextAgent(client=None)
    context = AgentContext(active_task_id="pipe_job_1")
    result = agent.evaluate("What is today's weather?", context=context)

    assert result.context_switch_detected is True
    assert result.preserve_task is True
    assert result.active_task_id == "pipe_job_1"
