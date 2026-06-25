"""Tests for desktop chat API."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.chat_service import list_chat_messages, send_chat_message
from api.desktop_service import DesktopApiService
from cli.session_store import SessionStore
from config.loader import CLIConfig
from engine.state.state_manager import TaskStateManager
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
