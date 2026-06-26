"""Behavioral tests for PlannerAgent."""

from __future__ import annotations

from ai.agents.planner_agent import PlannerAgent
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.agent import AgentAction, IntentResult


def test_planner_agent_returns_correct_root_for_pipe_workflow() -> None:
    agent = PlannerAgent(client=None)
    intent = IntentResult(
        intent=PIPE_WALL_THICKNESS_DESIGN,
        domain="piping",
        root_nodes=["tasks/asme_b31.3/pipe_wall_thickness_design/root.md"],
        confidence=0.95,
    )

    result = agent.plan(intent)

    assert result.root_nodes == ["pipe_wall_thickness_design"]
    assert "wall thickness" in " ".join(result.priorities).lower()
    assert result.action in {AgentAction.PROPOSE_PATH, AgentAction.REQUEST_INPUT}
