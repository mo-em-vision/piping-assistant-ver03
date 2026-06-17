"""Chat orchestrator tests."""

from __future__ import annotations

from ai.agents.intent_agent import IntentAgent
from cli.orchestrator import ChatOrchestrator
from engine.state.state_manager import TaskStateManager
from tests.agents.conftest import FakeLLMClient


def test_orchestrator_returns_waiting_input_for_pipe_thickness() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(
        manager,
        llm_client=FakeLLMClient({}),
    )
    response, _ = orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")

    assert response.status == "waiting_input"
    assert response.task_id is not None
    assert "design_pressure" in (response.data.get("missing_inputs") or [])
