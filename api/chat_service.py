"""Chat API helpers for the desktop application."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from cli.orchestrator import ChatOrchestrator
from cli.responses import CLIResponse
from cli.session_store import SessionStore
from config.loader import CLIConfig
from engine.state.state_manager import TaskNotFoundError, TaskStateManager

from api.serializers import task_state


def serialize_message(message: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id": str(message.get("id") or f"msg-{index}"),
        "role": str(message.get("role") or "assistant"),
        "content": str(message.get("content") or ""),
        "timestamp": str(message.get("timestamp") or ""),
        "status": message.get("status"),
    }


def list_chat_messages(store: SessionStore) -> list[dict[str, Any]]:
    return [serialize_message(message, index) for index, message in enumerate(store.load_conversation())]


def append_chat_message(
    store: SessionStore,
    *,
    role: str,
    content: str,
    status: str | None = None,
) -> dict[str, Any]:
    message = {
        "id": uuid4().hex,
        "role": role,
        "content": content,
        "timestamp": _utc_now(),
        "status": status,
    }
    messages = store.load_conversation()
    messages.append(message)
    store.save_conversation(messages)
    return message


def build_chat_context(task_state_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not task_state_payload:
        return {}

    progress = task_state_payload.get("progress") or {}
    return {
        "task_id": task_state_payload.get("task_id"),
        "workflow_id": task_state_payload.get("workflow_id"),
        "status": task_state_payload.get("status"),
        "current_step_id": progress.get("current_step_id"),
        "active_nodes": task_state_payload.get("active_nodes") or [],
        "missing_inputs": progress.get("missing_inputs") or [],
        "output_count": len(task_state_payload.get("display_outputs") or []),
    }


def send_chat_message(
    store: SessionStore,
    config: CLIConfig,
    manager: TaskStateManager,
    *,
    message: str,
    task_id: str | None = None,
    llm_client: Any | None = None,
) -> dict[str, Any]:
    text = message.strip()
    if not text:
        raise ValueError("message is required")

    if task_id:
        try:
            manager.set_active_task(task_id)
        except TaskNotFoundError:
            pass

    user_message = append_chat_message(store, role="user", content=text)

    orchestrator = ChatOrchestrator(
        manager,
        llm_client=llm_client,
        standards_root=config.standards_root,
    )
    response, _debug = orchestrator.handle_message(text)
    manager = orchestrator.state_manager

    if response.task_id:
        try:
            manager.set_active_task(response.task_id)
        except TaskNotFoundError:
            pass

    store.save_state_manager(manager)

    assistant_content = _assistant_content(response)
    assistant_message = append_chat_message(
        store,
        role="assistant",
        content=assistant_content,
        status=response.status,
    )

    task_state_payload = None
    if response.task_id:
        try:
            task = manager.get_task(response.task_id)
            task_state_payload = task_state(task, manager)
        except TaskNotFoundError:
            task_state_payload = None

    return {
        "session_id": store.session_id,
        "user_message": serialize_message(user_message, 0),
        "assistant_message": serialize_message(assistant_message, 1),
        "response": response.to_dict(),
        "context": build_chat_context(task_state_payload),
        "task_state": task_state_payload,
    }


def _assistant_content(response: CLIResponse) -> str:
    parts = [part for part in (response.message, response.question) if part]
    if parts:
        return "\n\n".join(parts)
    return response.status.replace("_", " ").title()


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
