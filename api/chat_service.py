"""Chat API helpers for the desktop application."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from cli.orchestrator import ChatOrchestrator
from cli.responses import CLIResponse
from cli.session_store import SessionStore
from config.loader import CLIConfig
from engine.state.state_manager import TaskNotFoundError, TaskStateManager

from ai.agents.selection_explain_agent import SelectionExplainAgent
from ai.agents.task_assist_agent import TaskAssistAgent
from api.chat_context import build_task_context_brief, prior_turns_for_llm
from api.serializers import task_state
from api.standards_retrieval import retrieve_standards_context
from engine.reference.standards_reader import StandardsReader


def serialize_message(message: dict[str, Any], index: int) -> dict[str, Any]:
    payload = {
        "id": str(message.get("id") or f"msg-{index}"),
        "role": str(message.get("role") or "assistant"),
        "content": str(message.get("content") or ""),
        "timestamp": str(message.get("timestamp") or ""),
        "status": message.get("status"),
        "task_id": message.get("task_id"),
    }
    sources = message.get("sources")
    if isinstance(sources, list) and sources:
        payload["sources"] = sources
    return payload


def _load_all_messages(store: SessionStore) -> list[dict[str, Any]]:
    return list(store.load_conversation())


def list_chat_messages(
    store: SessionStore,
    *,
    task_id: str | None = None,
) -> list[dict[str, Any]]:
    if task_id:
        messages = store.load_conversation(task_id)
    else:
        messages = store.load_conversation()
    return [serialize_message(message, index) for index, message in enumerate(messages)]


def clear_chat_messages(
    store: SessionStore,
    *,
    task_id: str | None = None,
) -> dict[str, Any]:
    if hasattr(store, "clear_conversation"):
        store.clear_conversation(task_id)
    else:
        store.save_conversation([])
    return {
        "session_id": store.session_id,
        "messages": list_chat_messages(store, task_id=task_id),
    }


def append_chat_message(
    store: SessionStore,
    *,
    role: str,
    content: str,
    status: str | None = None,
    task_id: str | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    message = {
        "id": uuid4().hex,
        "role": role,
        "content": content,
        "timestamp": _utc_now(),
        "status": status,
        "task_id": task_id,
    }
    if sources:
        message["sources"] = sources
    messages = _load_all_messages(store)
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


def _task_state_payload_for_chat(
    manager: TaskStateManager,
    task_id: str | None,
) -> dict[str, Any] | None:
    if not task_id:
        return None
    try:
        task = manager.get_task(task_id)
    except TaskNotFoundError:
        return None
    return task_state(task, manager)


def send_chat_message(
    store: SessionStore,
    config: CLIConfig,
    manager: TaskStateManager,
    *,
    message: str,
    display_message: str | None = None,
    task_id: str | None = None,
    mode: str | None = None,
    llm_client: Any | None = None,
    project_name: str | None = None,
) -> dict[str, Any]:
    text = message.strip()
    if not text:
        raise ValueError("message is required")

    if task_id:
        try:
            manager.set_active_task(task_id)
        except TaskNotFoundError:
            pass

    stored_user_content = (display_message or text).strip()
    user_message = append_chat_message(
        store,
        role="user",
        content=stored_user_content,
        task_id=task_id,
    )

    if mode == "selection_explain":
        return _send_selection_explanation(
            store,
            manager,
            user_message=user_message,
            prompt=text,
            task_id=task_id,
            llm_client=llm_client,
            project_name=project_name,
            standards_root=config.standards_root,
        )

    if task_id or mode == "task_assist":
        if not task_id:
            raise ValueError("task_id is required for task_assist mode")
        return _send_task_assist(
            store,
            manager,
            user_message=user_message,
            message=text,
            task_id=task_id,
            llm_client=llm_client,
            project_name=project_name,
            standards_root=config.standards_root,
        )

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
        task_state_payload = _task_state_payload_for_chat(manager, response.task_id)

    return {
        "session_id": store.session_id,
        "user_message": serialize_message(user_message, 0),
        "assistant_message": serialize_message(assistant_message, 1),
        "response": response.to_dict(),
        "context": build_chat_context(task_state_payload),
        "task_state": task_state_payload,
    }


def _send_task_assist(
    store: SessionStore,
    manager: TaskStateManager,
    *,
    user_message: dict[str, Any],
    message: str,
    task_id: str,
    llm_client: Any | None,
    project_name: str | None,
    standards_root: Path,
) -> dict[str, Any]:
    task_state_payload = _task_state_payload_for_chat(manager, task_id)
    context_brief = build_task_context_brief(task_state_payload, project_name=project_name)
    history = prior_turns_for_llm(_load_all_messages(store), task_id=task_id)

    reader = StandardsReader(standards_root)
    retrieval = retrieve_standards_context(
        message,
        reader=reader,
        task_state_payload=task_state_payload,
    )

    agent = TaskAssistAgent(client=llm_client)
    assist_reply = agent.reply(
        message,
        history=history,
        context_brief=context_brief,
        standards_context=retrieval.context_block,
        retrieval_sources=retrieval.source_dicts(),
    )

    assistant_message = append_chat_message(
        store,
        role="assistant",
        content=assist_reply.reply,
        status="assisted",
        task_id=task_id,
        sources=assist_reply.sources,
    )

    return {
        "session_id": store.session_id,
        "user_message": serialize_message(user_message, 0),
        "assistant_message": serialize_message(assistant_message, 1),
        "response": CLIResponse(
            status="assisted",
            message=assist_reply.reply,
            task_id=task_id,
        ).to_dict(),
        "context": build_chat_context(task_state_payload),
        "task_state": None,
    }


def _send_selection_explanation(
    store: SessionStore,
    manager: TaskStateManager,
    *,
    user_message: dict[str, Any],
    prompt: str,
    task_id: str | None,
    llm_client: Any | None,
    project_name: str | None,
    standards_root: Path,
) -> dict[str, Any]:
    task_state_payload = _task_state_payload_for_chat(manager, task_id)
    context_brief = build_task_context_brief(task_state_payload, project_name=project_name)
    history = prior_turns_for_llm(_load_all_messages(store), task_id=task_id)

    reader = StandardsReader(standards_root)
    retrieval = retrieve_standards_context(
        prompt,
        reader=reader,
        task_state_payload=task_state_payload,
    )

    agent = SelectionExplainAgent(client=llm_client)
    explain_reply = agent.explain(
        prompt,
        history=history,
        context_brief=context_brief,
        standards_context=retrieval.context_block,
        retrieval_sources=retrieval.source_dicts(),
    )

    assistant_message = append_chat_message(
        store,
        role="assistant",
        content=explain_reply.explanation,
        status="explained",
        task_id=task_id,
        sources=explain_reply.sources,
    )

    return {
        "session_id": store.session_id,
        "user_message": serialize_message(user_message, 0),
        "assistant_message": serialize_message(assistant_message, 1),
        "response": CLIResponse(
            status="explained",
            message=explain_reply.explanation,
            task_id=task_id,
        ).to_dict(),
        "context": build_chat_context(task_state_payload),
        "task_state": None,
    }


def _assistant_content(response: CLIResponse) -> str:
    parts = [part for part in (response.message, response.question) if part]
    if parts:
        return "\n\n".join(parts)
    return response.status.replace("_", " ").title()


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
