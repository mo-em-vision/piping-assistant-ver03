"""Tests for TaskContinuationAgent."""

from __future__ import annotations

from unittest.mock import patch

from ai.agents.task_continuation_agent import TaskContinuationAgent, fallback_suggestions
from ai.client import MissingAPIKeyError
from tests.agents.conftest import FakeLLMClient


def test_task_continuation_agent_returns_llm_suggestions() -> None:
    agent = TaskContinuationAgent(
        client=FakeLLMClient(
            {
                "suggestions": [
                    {
                        "id": "branch_connection_check",
                        "title": "Branch connection check",
                        "description": "Evaluate reinforcement for a branch on this line.",
                    }
                ]
            }
        ),
    )

    suggestions = agent.suggest(
        context_brief="Task: Pipe thickness (Piping)\nStatus: completed",
        workflow_id="pipe_wall_thickness_design",
    )

    assert len(suggestions) == 1
    assert suggestions[0]["id"] == "branch_connection_check"
    assert agent._client.calls  # type: ignore[attr-defined]


def test_task_continuation_agent_falls_back_without_api_key() -> None:
    agent = TaskContinuationAgent(client=None)

    with patch(
        "ai.agents.base.OpenAIClient.from_settings",
        side_effect=MissingAPIKeyError("OPENAI_API_KEY is not set."),
    ):
        suggestions = agent.suggest(workflow_id="pipe_wall_thickness_design")

    assert suggestions == fallback_suggestions("pipe_wall_thickness_design")


def test_task_continuation_agent_falls_back_on_empty_response() -> None:
    agent = TaskContinuationAgent(client=FakeLLMClient({"suggestions": []}))

    suggestions = agent.suggest(workflow_id="pipe_wall_thickness_design")

    assert suggestions == fallback_suggestions("pipe_wall_thickness_design")
