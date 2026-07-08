"""Repository operations for desktop SQLite storage."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from storage.desktop_database import DesktopDatabase, utc_now


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _task_status_from_payload(task_data: dict[str, Any]) -> str:
    status = task_data.get("status")
    if status:
        return str(status)
    execution_context = task_data.get("execution_context")
    if isinstance(execution_context, dict):
        context_status = execution_context.get("status")
        if context_status:
            return str(context_status)
    return "awaiting_input"


class ProjectRepository:
    def __init__(self, database: DesktopDatabase) -> None:
        self._db = database

    def list_projects(self) -> list[dict[str, Any]]:
        with self._db.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.active_task_id,
                    p.created_at,
                    p.updated_at,
                    COUNT(t.task_id) AS task_count
                FROM projects p
                LEFT JOIN project_tasks t ON t.project_id = p.id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self._db.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.active_task_id,
                    p.created_at,
                    p.updated_at,
                    COUNT(t.task_id) AS task_count
                FROM projects p
                LEFT JOIN project_tasks t ON t.project_id = p.id
                WHERE p.id = ?
                GROUP BY p.id
                """,
                (project_id,),
            ).fetchone()
        return dict(row) if row else None

    def ensure_project(self, project_id: str, *, name: str | None = None) -> dict[str, Any]:
        existing = self.get_project(project_id)
        if existing:
            return existing

        now = utc_now()
        display_name = name or project_id.replace("_", " ").replace("-", " ").title()
        with self._db.connect() as connection:
            connection.execute(
                """
                INSERT INTO projects (id, name, active_task_id, created_at, updated_at)
                VALUES (?, ?, NULL, ?, ?)
                """,
                (project_id, display_name, now, now),
            )
            connection.commit()
        created = self.get_project(project_id)
        assert created is not None
        return created

    def create_project(self, name: str) -> dict[str, Any]:
        project_id = f"project-{uuid4().hex[:8]}"
        now = utc_now()
        with self._db.connect() as connection:
            connection.execute(
                """
                INSERT INTO projects (id, name, active_task_id, created_at, updated_at)
                VALUES (?, ?, NULL, ?, ?)
                """,
                (project_id, name.strip(), now, now),
            )
            connection.commit()
        created = self.get_project(project_id)
        assert created is not None
        return created

    def delete_project(self, project_id: str) -> bool:
        existing = self.get_project(project_id)
        if existing is None:
            return False
        with self._db.connect() as connection:
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            connection.commit()
        return True

    def update_project_name(self, project_id: str, name: str) -> dict[str, Any] | None:
        existing = self.get_project(project_id)
        if existing is None:
            return None
        now = utc_now()
        with self._db.connect() as connection:
            connection.execute(
                """
                UPDATE projects
                SET name = ?, updated_at = ?
                WHERE id = ?
                """,
                (name.strip(), now, project_id),
            )
            connection.commit()
        return self.get_project(project_id)

    def touch_project(self, project_id: str, *, active_task_id: str | None = None) -> None:
        now = utc_now()
        with self._db.connect() as connection:
            if active_task_id is not None:
                connection.execute(
                    """
                    UPDATE projects
                    SET updated_at = ?, active_task_id = ?
                    WHERE id = ?
                    """,
                    (now, active_task_id, project_id),
                )
            else:
                connection.execute(
                    "UPDATE projects SET updated_at = ? WHERE id = ?",
                    (now, project_id),
                )
            connection.commit()

    def load_tasks_payload(self, project_id: str) -> dict[str, Any]:
        with self._db.connect() as connection:
            rows = connection.execute(
                """
                SELECT task_json
                FROM project_tasks
                WHERE project_id = ?
                ORDER BY updated_at ASC
                """,
                (project_id,),
            ).fetchall()
            project = connection.execute(
                "SELECT active_task_id FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()

        tasks = [json.loads(row["task_json"]) for row in rows]
        active_task_id = project["active_task_id"] if project else None
        return {
            "active_task_id": active_task_id,
            "tasks": tasks,
            "saved_at": utc_now(),
        }

    def save_tasks_payload(self, project_id: str, payload: dict[str, Any]) -> None:
        tasks = payload.get("tasks") or []
        active_task_id = payload.get("active_task_id")
        now = utc_now()

        with self._db.connect() as connection:
            connection.execute("DELETE FROM project_tasks WHERE project_id = ?", (project_id,))
            for task_data in tasks:
                if not isinstance(task_data, dict) or not task_data.get("task_id"):
                    continue
                task_id = str(task_data["task_id"])
                workflow = task_data.get("outputs", {}).get("workflow")
                connection.execute(
                    """
                    INSERT INTO project_tasks (
                        project_id, task_id, status, workflow_id, task_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        task_id,
                        _task_status_from_payload(task_data),
                        str(workflow) if workflow else None,
                        json.dumps(task_data, default=_json_default),
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO task_artifacts (project_id, task_id, kind, payload_json, updated_at)
                    VALUES (?, ?, 'state', ?, ?)
                    ON CONFLICT(project_id, task_id, kind)
                    DO UPDATE SET payload_json = excluded.payload_json, updated_at = excluded.updated_at
                    """,
                    (project_id, task_id, json.dumps(task_data, default=_json_default), now),
                )

            connection.execute(
                """
                UPDATE projects
                SET active_task_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (active_task_id, now, project_id),
            )
            connection.commit()

    def load_conversation(
        self,
        project_id: str,
        *,
        task_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._db.connect() as connection:
            if task_id:
                rows = connection.execute(
                    """
                    SELECT id, role, content, status, timestamp, task_id, sources_json
                    FROM chat_messages
                    WHERE project_id = ? AND task_id = ?
                    ORDER BY timestamp ASC
                    """,
                    (project_id, task_id),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT id, role, content, status, timestamp, task_id, sources_json
                    FROM chat_messages
                    WHERE project_id = ?
                    ORDER BY timestamp ASC
                    """,
                    (project_id,),
                ).fetchall()
        messages: list[dict[str, Any]] = []
        for row in rows:
            message = {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "status": row["status"],
                "timestamp": row["timestamp"],
                "task_id": row["task_id"],
            }
            sources_json = row["sources_json"]
            if sources_json:
                try:
                    sources = json.loads(sources_json)
                except json.JSONDecodeError:
                    sources = None
                if isinstance(sources, list) and sources:
                    message["sources"] = sources
            messages.append(message)
        return messages

    def clear_conversation(
        self,
        project_id: str,
        *,
        task_id: str | None = None,
    ) -> None:
        with self._db.connect() as connection:
            if task_id:
                connection.execute(
                    "DELETE FROM chat_messages WHERE project_id = ? AND task_id = ?",
                    (project_id, task_id),
                )
            else:
                connection.execute(
                    "DELETE FROM chat_messages WHERE project_id = ?",
                    (project_id,),
                )
            connection.commit()
        self.touch_project(project_id)

    def save_conversation(self, project_id: str, messages: list[dict[str, Any]]) -> None:
        now = utc_now()
        with self._db.connect() as connection:
            connection.execute("DELETE FROM chat_messages WHERE project_id = ?", (project_id,))
            for message in messages:
                sources = message.get("sources")
                sources_json = (
                    json.dumps(sources, ensure_ascii=False)
                    if isinstance(sources, list) and sources
                    else None
                )
                connection.execute(
                    """
                    INSERT INTO chat_messages (
                        id, project_id, task_id, role, content, status, timestamp, sources_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(message.get("id") or uuid4().hex),
                        project_id,
                        message.get("task_id"),
                        str(message.get("role") or "assistant"),
                        str(message.get("content") or ""),
                        message.get("status"),
                        str(message.get("timestamp") or now),
                        sources_json,
                    ),
                )
            connection.commit()
        self.touch_project(project_id)

    def save_task_artifact(
        self,
        project_id: str,
        task_id: str,
        *,
        kind: str,
        payload_json: str,
    ) -> None:
        now = utc_now()
        with self._db.connect() as connection:
            connection.execute(
                """
                INSERT INTO task_artifacts (project_id, task_id, kind, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id, task_id, kind)
                DO UPDATE SET payload_json = excluded.payload_json, updated_at = excluded.updated_at
                """,
                (project_id, task_id, kind, payload_json, now),
            )
            connection.commit()
        self.touch_project(project_id)

    def list_recent_tasks(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._db.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    pt.project_id,
                    pt.task_id,
                    pt.status,
                    pt.workflow_id,
                    pt.task_json,
                    pt.updated_at,
                    p.name AS project_name
                FROM project_tasks pt
                JOIN projects p ON p.id = pt.project_id
                WHERE pt.status NOT IN ('completed', 'invalidated')
                ORDER BY pt.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
