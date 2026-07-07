"""Intent agent deterministic MAWP routing."""

from __future__ import annotations

from ai.agents.intent_agent import IntentAgent
from engine.router import MAWP_DESIGN


def test_intent_agent_routes_mawp_deterministically() -> None:
    agent = IntentAgent()
    result = agent.analyze("Calculate MAWP for a 6 inch pipe")
    assert result.workflow == MAWP_DESIGN
    assert result.confidence >= 0.9
    assert result.root_nodes == ["WF-MAWP"]
