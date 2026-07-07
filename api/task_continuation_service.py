"""Continuation suggestion helpers for completed tasks."""

from __future__ import annotations

from typing import Any

from ai.agents.task_continuation_agent import TaskContinuationAgent
from api.chat_context import build_task_context_brief
from api.serializers import task_state
from storage.session_store import SessionStore
from config.loader import CLIConfig
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


def get_continuation_suggestions(
    store: SessionStore,
    config: CLIConfig,
    manager: TaskStateManager,
    task_id: str,
    *,
    reader: StandardsReader,
    project_name: str | None = None,
    agent: TaskContinuationAgent | None = None,
) -> dict[str, Any]:
    task = manager.get_task(task_id)
    if task.status != TaskStatus.COMPLETED:
        raise ValueError("Task must be completed to load continuation suggestions")

    state_payload = task_state(
        task,
        manager,
        standards_root=config.standards_root,
        reader=reader,
    )
    workflow_id = str(state_payload.get("workflow_id") or "").strip()
    context_brief = build_task_context_brief(state_payload, project_name=project_name)
    continuation_agent = agent or TaskContinuationAgent()
    suggestions = continuation_agent.suggest(
        context_brief=context_brief,
        workflow_id=workflow_id,
    )

    return {
        "task_id": task_id,
        "workflow_id": workflow_id,
        "suggestions": suggestions,
    }
