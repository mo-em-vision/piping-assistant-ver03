"""SQLite-backed project session storage for the desktop API."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from storage.session_store import _input_from_dict, _input_to_dict, _task_from_dict, _task_to_dict
from engine.state.state_manager import TaskAlreadyExistsError, TaskNotFoundError, TaskStateManager
from models.task import Task, TaskStatus
from storage.desktop_database import DesktopDatabase
from storage.migrate_legacy_sessions import migrate_legacy_sessions
from storage.project_repository import ProjectRepository


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


class ProjectSessionStore:
    """Session-compatible store backed by SQLite with filesystem report paths."""

    def __init__(self, database: DesktopDatabase, sessions_dir: Path, session_id: str | None = None) -> None:
        migrate_legacy_sessions(database, sessions_dir)
        self.database = database
        self.sessions_dir = sessions_dir
        self.repository = ProjectRepository(database)
        if not session_id:
            raise ValueError("session_id is required")
        self.session_id = session_id
        self.session_path = sessions_dir / self.session_id
        self.session_path.mkdir(parents=True, exist_ok=True)
        (self.session_path / "reports").mkdir(exist_ok=True)

    @classmethod
    def list_sessions(cls, database: DesktopDatabase) -> list[str]:
        return [row["id"] for row in ProjectRepository(database).list_projects()]

    def load_state_manager(self) -> TaskStateManager:
        manager = TaskStateManager()
        payload = self.repository.load_tasks_payload(self.session_id)

        for task_data in payload.get("tasks", []):
            if not isinstance(task_data, dict):
                continue
            task = _task_from_dict(task_data)
            try:
                manager.create_task(task.task_id, status=task.status, set_active=False)
            except TaskAlreadyExistsError:
                manager.replace_task(task.task_id, task)
            else:
                manager.replace_task(task.task_id, task)

        active_task_id = payload.get("active_task_id")
        if active_task_id:
            try:
                manager.set_active_task(str(active_task_id))
            except TaskNotFoundError:
                pass

        return manager

    def save_state_manager(self, manager: TaskStateManager) -> None:
        active = manager.get_active_task()
        payload = {
            "active_task_id": active.task_id if active else None,
            "tasks": [_task_to_dict(task) for task in manager.list_tasks()],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        self.repository.save_tasks_payload(self.session_id, payload)

        tasks_path = self.session_path / "tasks.json"
        tasks_path.write_text(
            json.dumps(payload, indent=2, default=_json_default),
            encoding="utf-8",
        )

    def load_conversation(self, task_id: str | None = None) -> list[dict[str, str]]:
        return self.repository.load_conversation(self.session_id, task_id=task_id)

    def save_conversation(self, messages: list[dict[str, str]]) -> None:
        self.repository.save_conversation(self.session_id, messages)
        conversation_path = self.session_path / "conversation.json"
        conversation_path.write_text(json.dumps(messages, indent=2), encoding="utf-8")

    def clear_conversation(self, task_id: str | None = None) -> None:
        self.repository.clear_conversation(self.session_id, task_id=task_id)
        conversation_path = self.session_path / "conversation.json"
        remaining = self.repository.load_conversation(self.session_id)
        conversation_path.write_text(json.dumps(remaining, indent=2), encoding="utf-8")

    def append_message(self, role: str, content: str) -> None:
        messages = self.load_conversation()
        messages.append(
            {
                "id": uuid4().hex,
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.save_conversation(messages)

    def incomplete_tasks(self, manager: TaskStateManager) -> list[Task]:
        terminal = {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}
        return [task for task in manager.list_tasks() if task.status not in terminal]


def open_project_store(config_sessions_dir: Path, project_id: str, db_path: Path | None = None) -> ProjectSessionStore:
    resolved_db = db_path or (config_sessions_dir.parent / "data" / "desktop.db")
    database = DesktopDatabase(resolved_db)
    return ProjectSessionStore(database, config_sessions_dir, session_id=project_id)


def list_project_summaries(database: DesktopDatabase) -> list[dict[str, Any]]:
    repository = ProjectRepository(database)
    projects = repository.list_projects()
    return [
        {
            "id": project["id"],
            "name": project["name"],
            "task_count": int(project["task_count"] or 0),
            "updated_at": project["updated_at"],
            "active_task_id": project.get("active_task_id"),
        }
        for project in projects
    ]


def get_database_for_config(sessions_dir: Path) -> DesktopDatabase:
    return DesktopDatabase(sessions_dir.parent / "data" / "desktop.db")
