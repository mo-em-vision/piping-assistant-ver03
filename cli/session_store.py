"""Persist session conversation and task state to sessions/."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from engine.state.state_manager import TaskAlreadyExistsError, TaskNotFoundError, TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task, TaskStatus


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


class SessionStore:
    """Filesystem-backed session storage under sessions/<session_id>/."""

    def __init__(self, sessions_dir: Path, session_id: str | None = None) -> None:
        self.sessions_dir = sessions_dir
        self.session_id = session_id or self._default_session_id()
        self.session_path = sessions_dir / self.session_id
        self.session_path.mkdir(parents=True, exist_ok=True)
        (self.session_path / "reports").mkdir(exist_ok=True)

    @staticmethod
    def _default_session_id() -> str:
        return "default"

    @classmethod
    def list_sessions(cls, sessions_dir: Path) -> list[str]:
        if not sessions_dir.exists():
            return []
        return sorted(
            path.name
            for path in sessions_dir.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )

    def load_state_manager(self) -> TaskStateManager:
        manager = TaskStateManager()
        tasks_path = self.session_path / "tasks.json"
        if not tasks_path.exists():
            return manager

        payload = json.loads(tasks_path.read_text(encoding="utf-8"))
        for task_data in payload.get("tasks", []):
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
                manager.set_active_task(active_task_id)
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
        (self.session_path / "tasks.json").write_text(
            json.dumps(payload, indent=2, default=_json_default),
            encoding="utf-8",
        )

    def load_conversation(self) -> list[dict[str, str]]:
        path = self.session_path / "conversation.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def save_conversation(self, messages: list[dict[str, str]]) -> None:
        (self.session_path / "conversation.json").write_text(
            json.dumps(messages, indent=2),
            encoding="utf-8",
        )

    def append_message(self, role: str, content: str) -> None:
        messages = self.load_conversation()
        messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.save_conversation(messages)

    def incomplete_tasks(self, manager: TaskStateManager) -> list[Task]:
        terminal = {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}
        return [task for task in manager.list_tasks() if task.status not in terminal]


def _task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "active_nodes": task.active_nodes,
        "inputs": {key: _input_to_dict(value) for key, value in task.inputs.items()},
        "outputs": task.outputs,
        "warnings": task.warnings,
        "conflicts": [asdict(conflict) for conflict in task.conflicts],
    }


def _task_from_dict(data: dict[str, Any]) -> Task:
    return Task(
        task_id=data["task_id"],
        status=TaskStatus(data["status"]),
        active_nodes=list(data.get("active_nodes", [])),
        inputs={
            key: _input_from_dict(value) for key, value in data.get("inputs", {}).items()
        },
        outputs=dict(data.get("outputs", {})),
        warnings=list(data.get("warnings", [])),
    )


def _input_to_dict(inp: EngineeringInput) -> dict[str, Any]:
    return {
        "input_id": inp.input_id,
        "value": inp.value,
        "unit": inp.unit,
        "source": inp.source.value,
        "status": inp.status.value,
        "default": inp.default,
        "requires_confirmation": inp.requires_confirmation,
        "uncertainty": inp.uncertainty,
        "original_value": inp.original_value,
        "original_unit": inp.original_unit,
    }


def _input_from_dict(data: dict[str, Any]) -> EngineeringInput:
    return EngineeringInput(
        input_id=data["input_id"],
        value=data["value"],
        unit=data["unit"],
        source=InputSource(data["source"]),
        status=InputStatus(data.get("status", InputStatus.PENDING.value)),
        default=data.get("default"),
        requires_confirmation=bool(data.get("requires_confirmation", False)),
        uncertainty=data.get("uncertainty"),
        original_value=data.get("original_value"),
        original_unit=data.get("original_unit"),
    )


def new_task_id(workflow: str) -> str:
    suffix = uuid4().hex[:6]
    slug = workflow.replace("_", "-")[:24]
    return f"{slug}-{suffix}"
