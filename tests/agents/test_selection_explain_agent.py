"""Tests for SelectionExplainAgent."""

from __future__ import annotations

from unittest.mock import patch

from ai.agents.selection_explain_agent import SelectionExplainAgent
from ai.client import MissingAPIKeyError
from engine.reference.asme_b31_3_table_ids import TABLE_304_1_1, TABLE_A_1A
from tests.agents.conftest import FakeLLMClient


def test_selection_explain_agent_returns_explanation() -> None:
    agent = SelectionExplainAgent(
        client=FakeLLMClient(
            {
                "explanation": (
                    "The quality factor (E) is a multiplier in the wall-thickness equation."
                )
            }
        ),
    )

    reply = agent.explain("Explain quality factor with an example.")

    assert "quality factor" in reply.explanation.lower()
    assert agent._client.message_calls  # type: ignore[attr-defined]


def test_selection_explain_agent_normalizes_sources() -> None:
    fallback = [
        {
            "kind": "table",
            "id": TABLE_304_1_1,
            "label": "Table 304.1.1 — Temperature Coefficient Y",
            "table_id": TABLE_304_1_1,
        }
    ]
    agent = SelectionExplainAgent(
        client=FakeLLMClient(
            {
                "explanation": "Y comes from [Table 304.1.1](table:asme_b31.3_table_304_1_1).",
                "sources": [
                    {
                        "kind": "table",
                        "id": TABLE_304_1_1,
                        "label": "Table 304.1.1 — Temperature Coefficient Y",
                        "table_id": TABLE_304_1_1,
                    }
                ],
            }
        ),
    )

    reply = agent.explain(
        "Explain temperature coefficient Y.",
        retrieval_sources=fallback,
    )

    assert reply.sources
    assert reply.sources[0]["id"] == TABLE_304_1_1


def test_selection_explain_agent_falls_back_to_retrieval_sources() -> None:
    fallback = [
        {
            "kind": "table",
            "id": TABLE_A_1A,
            "label": "Table A-1A — Quality Factors",
            "table_id": TABLE_A_1A,
        }
    ]
    agent = SelectionExplainAgent(
        client=FakeLLMClient(
            {
                "explanation": "Quality factor E is listed in Table A-1A.",
            }
        ),
    )

    reply = agent.explain(
        "Explain quality factor.",
        retrieval_sources=fallback,
    )

    assert reply.sources == fallback


def test_selection_explain_agent_without_client_returns_configuration_message() -> None:
    agent = SelectionExplainAgent(client=None)

    with patch(
        "ai.agents.base.OpenAIClient.from_settings",
        side_effect=MissingAPIKeyError("OPENAI_API_KEY is not set."),
    ):
        reply = agent.explain("Explain quality factor.")

    assert "OPENAI_API_KEY" in reply.explanation
