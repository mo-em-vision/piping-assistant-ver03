"""Tests for desktop chat API."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.chat_service import clear_chat_messages, list_chat_messages, send_chat_message
from api.desktop_service import DesktopApiService
from cli.session_store import SessionStore
from config.loader import CLIConfig
from engine.state.state_manager import TaskStateManager
from engine.reference.asme_b31_3_table_ids import TABLE_304_1_1
from tests.agents.conftest import FakeLLMClient


@pytest.fixture
def temp_config(tmp_path: Path) -> CLIConfig:
    sessions_dir = tmp_path / "sessions"
    standards_root = Path(__file__).resolve().parents[2] / "standards"
    return CLIConfig(
        report_format="pdf",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=sessions_dir,
        standards_root=standards_root,
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )


def test_list_chat_messages_empty(temp_config: CLIConfig) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-test")
    messages = list_chat_messages(store)
    assert messages == []


def test_send_chat_message_returns_assistant_reply(temp_config: CLIConfig) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-test-send")
    manager = TaskStateManager()

    result = send_chat_message(
        store,
        temp_config,
        manager,
        message="Calculate pipe wall thickness for refinery piping",
        llm_client=FakeLLMClient({}),
    )

    assert result["user_message"]["role"] == "user"
    assert result["assistant_message"]["role"] == "assistant"
    assert result["assistant_message"]["content"]
    assert result["response"]["status"] in {"waiting_input", "ready", "clarify"}
    assert len(list_chat_messages(store)) == 2


def test_send_chat_message_uses_display_message_for_stored_user_content(
    temp_config: CLIConfig,
) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-test-display")
    manager = TaskStateManager()
    full_prompt = (
        'The user selected """t = 12.5 mm""" from task "Pipe Thickness". '
        "Explain this in context."
    )
    display_text = "t = 12.5 mm"

    result = send_chat_message(
        store,
        temp_config,
        manager,
        message=full_prompt,
        display_message=display_text,
        llm_client=FakeLLMClient({}),
    )

    assert result["user_message"]["content"] == display_text
    stored = list_chat_messages(store)
    assert stored[0]["content"] == display_text
    assert stored[0]["content"] != full_prompt


def test_send_chat_message_selection_explain_bypasses_workflow_prompt(
    temp_config: CLIConfig,
) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-test-selection")
    manager = TaskStateManager()
    fake_client = FakeLLMClient(
        {
            "explanation": (
                "The quality factor (E) adjusts allowable strength in the wall-thickness equation. "
                "For seamless pipe it is often 1.0."
            )
        }
    )

    result = send_chat_message(
        store,
        temp_config,
        manager,
        message=(
            "The user highlighted quality factor. Explain definition and examples. "
            "Do not ask for inputs."
        ),
        display_message="quality factor",
        mode="selection_explain",
        llm_client=fake_client,
    )

    assert result["user_message"]["content"] == "quality factor"
    assert result["assistant_message"]["content"].startswith("The quality factor")
    assert result["response"]["status"] == "explained"
    assert result["task_state"] is None
    assert "Missing parameters" not in result["assistant_message"]["content"]
    assert fake_client.message_calls
    system_prompt, _ = fake_client.message_calls[0]
    assert "Retrieved standards sources" in system_prompt


def test_send_chat_message_selection_explain_includes_sources(
    temp_config: CLIConfig,
) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-test-selection-sources")
    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-selection"
    manager.create_task(task_id)

    fake_client = FakeLLMClient(
        {
            "explanation": (
                "The temperature coefficient Y is from "
                "[Table 304.1.1](table:asme_b31.3_table_304_1_1)."
            ),
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

    result = send_chat_message(
        store,
        temp_config,
        manager,
        message="Explain temperature coefficient Y from Table 304.1.1.",
        display_message="temperature coefficient",
        task_id=task_id,
        mode="selection_explain",
        llm_client=fake_client,
    )

    sources = result["assistant_message"].get("sources") or []
    assert sources
    assert any(
        source.get("table_id") == TABLE_304_1_1 or source.get("id") == TABLE_304_1_1
        for source in sources
    )
    stored = list_chat_messages(store, task_id=task_id)
    assert stored[-1].get("sources")


def test_send_chat_message_task_assist_returns_conversational_reply(
    temp_config: CLIConfig,
) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-test-assist")
    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-001"
    manager.create_task(task_id)

    fake_client = FakeLLMClient(
        {"reply": "Weld joint efficiency (E) is often 1.0 for seamless pipe."}
    )
    result = send_chat_message(
        store,
        temp_config,
        manager,
        message="What is weld joint efficiency?",
        task_id=task_id,
        mode="task_assist",
        llm_client=fake_client,
    )

    assert result["response"]["status"] == "assisted"
    assert "weld joint efficiency" in result["assistant_message"]["content"].lower()
    assert result["task_state"] is None
    assert result["user_message"]["task_id"] == task_id
    assert fake_client.message_calls
    system_prompt, _ = fake_client.message_calls[0]
    assert "Retrieved standards sources" in system_prompt


def test_send_chat_message_task_assist_includes_sources_for_y_coefficient(
    temp_config: CLIConfig,
) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-test-assist-y")
    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-y"
    manager.create_task(task_id)

    fake_client = FakeLLMClient(
        {
            "reply": "Typical Y values are listed in Table 304.1.1 (ASME B31.3 §304.1.1).",
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
    result = send_chat_message(
        store,
        temp_config,
        manager,
        message="What are typical values for the Y coefficient?",
        task_id=task_id,
        mode="task_assist",
        llm_client=fake_client,
    )

    sources = result["assistant_message"].get("sources") or []
    assert sources
    assert any(source.get("table_id") == TABLE_304_1_1 or source.get("id") == TABLE_304_1_1 for source in sources)
    stored = list_chat_messages(store, task_id=task_id)
    assert stored[-1].get("sources")


def test_send_chat_message_task_assist_includes_prior_turns(
    temp_config: CLIConfig,
) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-test-assist-history")
    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-002"
    manager.create_task(task_id)
    fake_client = FakeLLMClient({"reply": "Follow-up answer about E."})

    send_chat_message(
        store,
        temp_config,
        manager,
        message="What is E?",
        task_id=task_id,
        mode="task_assist",
        llm_client=fake_client,
    )

    fake_client.message_calls.clear()
    fake_client.response = {"reply": "Another example for E."}
    send_chat_message(
        store,
        temp_config,
        manager,
        message="Can you give another example?",
        task_id=task_id,
        mode="task_assist",
        llm_client=fake_client,
    )

    assert fake_client.message_calls
    _, messages = fake_client.message_calls[0]
    assert messages[0]["content"] == "What is E?"
    assert messages[-1]["content"] == "Can you give another example?"


def test_list_and_clear_chat_messages_scoped_by_task_id(temp_config: CLIConfig) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-test-scope")
    store.save_conversation(
        [
            {
                "id": "1",
                "role": "user",
                "content": "Task A",
                "task_id": "task-a",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
            {
                "id": "2",
                "role": "user",
                "content": "Task B",
                "task_id": "task-b",
                "timestamp": "2026-01-01T00:00:01+00:00",
            },
        ]
    )

    assert len(list_chat_messages(store, task_id="task-a")) == 1
    clear_chat_messages(store, task_id="task-a")
    assert list_chat_messages(store, task_id="task-a") == []
    assert len(list_chat_messages(store, task_id="task-b")) == 1


def test_desktop_service_chat_endpoints(temp_config: CLIConfig) -> None:
    from tests.api.conftest import api_session_id

    service = DesktopApiService(config=temp_config, session_id="chat-service-test")
    session_id = api_session_id(service, "Chat Test Project")
    listed = service.list_chat_messages(session_id)
    assert listed["messages"] == []

    sent = service.post_chat_message(
        "Calculate pipe wall thickness for refinery piping",
        session_id=session_id,
    )
    assert sent["assistant_message"]["content"]
    assert service.list_chat_messages(session_id)["messages"]


def test_clear_chat_messages_empties_conversation(temp_config: CLIConfig) -> None:
    from tests.api.conftest import api_session_id

    service = DesktopApiService(config=temp_config, session_id="chat-clear-test")
    session_id = api_session_id(service, "Chat Clear Project")
    service.post_chat_message(
        "Calculate pipe wall thickness for refinery piping",
        session_id=session_id,
    )
    assert service.list_chat_messages(session_id)["messages"]

    cleared = service.clear_chat_messages(session_id)
    assert cleared["session_id"] == session_id
    assert cleared["messages"] == []
    assert service.list_chat_messages(session_id)["messages"] == []


def test_clear_chat_messages_service_helper(temp_config: CLIConfig) -> None:
    store = SessionStore(temp_config.sessions_dir, session_id="chat-clear-helper")
    store.save_conversation(
        [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": "2026-01-01T00:00:00+00:00",
            }
        ]
    )

    result = clear_chat_messages(store)

    assert result["messages"] == []
    assert list_chat_messages(store) == []
