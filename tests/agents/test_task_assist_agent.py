"""Tests for TaskAssistAgent."""

from __future__ import annotations

from unittest.mock import patch

from ai.agents.task_assist_agent import TaskAssistAgent
from ai.client import MissingAPIKeyError
from engine.reference.asme_b31_3_table_ids import TABLE_304_1_1
from tests.agents.conftest import FakeLLMClient


def test_task_assist_agent_returns_reply_with_history() -> None:
    fake_client = FakeLLMClient({"reply": "Here is another example for quality factor (E)."})
    agent = TaskAssistAgent(client=fake_client)

    assist_reply = agent.reply(
        "Can you give another example?",
        history=[{"role": "user", "content": "What is E?"}],
        context_brief="Task: Pipe thickness",
    )

    assert "quality factor" in assist_reply.reply.lower()
    assert fake_client.message_calls
    _, messages = fake_client.message_calls[0]
    assert messages[0]["content"] == "What is E?"
    assert messages[-1]["content"] == "Can you give another example?"


def test_task_assist_agent_includes_standards_context_in_system_prompt() -> None:
    fake_client = FakeLLMClient(
        {
            "reply": "Y is from Table 304.1.1 per ASME B31.3 §304.1.1.",
            "sources": [
                {
                    "kind": "table",
                    "id": TABLE_304_1_1,
                    "label": "Table 304.1.1 — Temperature Coefficient Y",
                    "paragraph": "304.1.1",
                    "node_id": "B313-table-304-1-1",
                }
            ],
        }
    )
    agent = TaskAssistAgent(client=fake_client)
    fallback_sources = [
        {
            "kind": "table",
            "id": TABLE_304_1_1,
            "label": "Table 304.1.1 — Temperature Coefficient Y",
            "paragraph": "304.1.1",
            "table_id": TABLE_304_1_1,
            "node_id": "B313-table-304-1-1",
        }
    ]

    assist_reply = agent.reply(
        "What is Y?",
        standards_context="#### Source 1: Table 304.1.1",
        retrieval_sources=fallback_sources,
    )

    assert assist_reply.sources
    assert assist_reply.sources[0]["id"] == TABLE_304_1_1
    system_prompt, _ = fake_client.message_calls[0]
    assert "Retrieved standards sources" in system_prompt
    assert "Table 304.1.1" in system_prompt


def test_task_assist_agent_falls_back_to_retrieval_sources_when_llm_omits_them() -> None:
    fake_client = FakeLLMClient({"reply": "Answer grounded in the table."})
    agent = TaskAssistAgent(client=fake_client)
    fallback_sources = [
        {
            "kind": "table",
            "id": TABLE_304_1_1,
            "label": "Table 304.1.1 — Temperature Coefficient Y",
            "table_id": TABLE_304_1_1,
        }
    ]

    assist_reply = agent.reply(
        "What is Y?",
        standards_context="table excerpt",
        retrieval_sources=fallback_sources,
    )

    assert assist_reply.sources == fallback_sources


def test_task_assist_agent_without_client_returns_configuration_message() -> None:
    agent = TaskAssistAgent(client=None)

    with patch(
        "ai.agents.base.OpenAIClient.from_settings",
        side_effect=MissingAPIKeyError("OPENAI_API_KEY is not set."),
    ):
        assist_reply = agent.reply("Explain weld joint efficiency.")

    assert "OPENAI_API_KEY" in assist_reply.reply
