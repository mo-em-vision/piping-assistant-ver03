"""Persist session conversation and task state to sessions/."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from engine.state.authority_context_migration import migrate_task_to_v5
from engine.state.execution_context_sync import refresh_execution_context_for_task
from engine.state.goal_migration import migrate_task_goals_from_outputs
from engine.state.state_manager import TaskAlreadyExistsError, TaskNotFoundError, TaskStateManager
from models.authority_context import authority_context_from_dict, authority_context_to_dict
from models.execution_context import execution_context_from_dict, execution_context_to_dict
from models.input import EngineeringInput, InputSource, InputStatus, ParameterDescriptor
from models.task import Task, TaskStatus, new_task


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

    def load_conversation(self, task_id: str | None = None) -> list[dict[str, str]]:
        path = self.session_path / "conversation.json"
        if not path.exists():
            return []
        messages = json.loads(path.read_text(encoding="utf-8"))
        if task_id:
            return [message for message in messages if message.get("task_id") == task_id]
        return messages

    def save_conversation(self, messages: list[dict[str, str]]) -> None:
        (self.session_path / "conversation.json").write_text(
            json.dumps(messages, indent=2),
            encoding="utf-8",
        )

    def clear_conversation(self, task_id: str | None = None) -> None:
        if task_id:
            remaining = [
                message
                for message in self.load_conversation()
                if message.get("task_id") != task_id
            ]
            self.save_conversation(remaining)
            return
        self.save_conversation([])

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
    payload: dict[str, Any] = {
        "task_id": task.task_id,
        "active_nodes": task.active_nodes,
        "execution_context": execution_context_to_dict(task.execution_context),
        "outputs": task.outputs,
        "parameter_registry": {
            key: _descriptor_to_dict(value) for key, value in task.parameter_registry.items()
        },
        "payload_version": task.payload_version,
    }
    if task.authority_context is not None:
        payload["authority_context"] = authority_context_to_dict(task.authority_context)
    return payload


def _task_from_dict(data: dict[str, Any]) -> Task:
    migrated = migrate_task_to_v5(data)
    ctx = execution_context_from_dict(migrated["execution_context"])

    registry_raw = migrated.get("parameter_registry") or {}
    registry = {
        key: _descriptor_from_dict(value) for key, value in registry_raw.items()
    }

    authority_context = None
    if migrated.get("authority_context"):
        authority_context = authority_context_from_dict(migrated["authority_context"])

    task = Task(
        task_id=migrated["task_id"],
        execution_context=ctx,
        authority_context=authority_context,
        active_nodes=list(migrated.get("active_nodes", [])),
        outputs=dict(migrated.get("outputs", {})),
        parameter_registry=registry,
        payload_version=int(migrated.get("payload_version", 5)),
    )
    migrate_task_goals_from_outputs(task)
    refresh_execution_context_for_task(task)
    return task


def _descriptor_to_dict(desc: ParameterDescriptor) -> dict[str, Any]:
    return asdict(desc)


def _descriptor_from_dict(data: dict[str, Any]) -> ParameterDescriptor:
    from models.input import ResolutionMethod, ResolutionRef

    resolution_ref = None
    if data.get("resolution_ref"):
        resolution_ref = ResolutionRef(**data["resolution_ref"])
    resolution_method = None
    if data.get("resolution_method"):
        resolution_method = ResolutionMethod(data["resolution_method"])
    return ParameterDescriptor(
        input_id=data["input_id"],
        symbol=data["symbol"],
        description=data["description"],
        introduced_at_node=data["introduced_at_node"],
        unit=data.get("unit", "dimensionless"),
        defined_in_nodes=tuple(data.get("defined_in_nodes") or ()),
        concept_id=data.get("concept_id"),
        resolution_method=resolution_method,
        resolution_ref=resolution_ref,
        required_when_nodes=tuple(data.get("required_when_nodes") or ()),
        status=InputStatus(data.get("status", InputStatus.PENDING.value)),
    )


def _input_to_dict(inp: EngineeringInput) -> dict[str, Any]:
    """Legacy EngineeringInput JSON shape for project session storage."""
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
