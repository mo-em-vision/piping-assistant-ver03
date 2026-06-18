"""Behavioral tests for IntentAgent."""

from __future__ import annotations

from ai.agents.intent_agent import IntentAgent
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.agent import AgentAction, AgentContext
from tests.agents.conftest import FakeLLMClient


def test_intent_agent_wraps_router_for_pipe_thickness() -> None:
    agent = IntentAgent(client=FakeLLMClient({}))
    result = agent.analyze("Design pipe thickness for refinery service")

    assert result.intent == PIPE_WALL_THICKNESS_DESIGN
    assert result.domain == "piping"
    assert "ASME B31.3" in result.possible_standards
    assert result.root_nodes == ["roots/pipe_wall_thickness_design/root.md"]
    assert result.confidence >= 0.9
    assert result.action == AgentAction.PROPOSE_PATH
    assert len(agent.client.calls) == 0


def test_intent_agent_llm_fallback_when_router_unmatched() -> None:
    fake = FakeLLMClient(
        {
            "intent": PIPE_WALL_THICKNESS_DESIGN,
            "domain": "piping",
            "possible_standards": ["ASME B31.3"],
            "root_nodes": ["roots/pipe_wall_thickness_design/root.md"],
            "missing_context": ["design_pressure"],
            "confidence": 0.8,
            "action": "propose_path",
        }
    )
    agent = IntentAgent(client=fake)
    result = agent.analyze("Need help sizing a line for hot oil service")

    assert result.intent == PIPE_WALL_THICKNESS_DESIGN
    assert fake.calls


def test_intent_agent_continues_active_workflow_without_llm() -> None:
    agent = IntentAgent(client=FakeLLMClient({}))
    context = AgentContext(
        active_task_id="pipe-wall-thickness-task-1",
        workflow=PIPE_WALL_THICKNESS_DESIGN,
        missing_inputs=["design_pressure", "outside_diameter"],
        user_message="material ASTM A106, Temperature: 85 Celcius, Pressure: 4 inch",
    )
    result = agent.analyze(context.user_message or "", context=context)

    assert result.intent == PIPE_WALL_THICKNESS_DESIGN
    assert result.action == AgentAction.PROPOSE_PATH
    assert result.confidence >= 0.9
    assert "design_pressure" in result.missing_context
    assert "outside_diameter" in result.missing_context
    assert len(agent.client.calls) == 0
