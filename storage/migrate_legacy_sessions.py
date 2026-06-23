"""Migrate legacy filesystem sessions into SQLite."""

from __future__ import annotations

import json
from pathlib import Path

from storage.desktop_database import DesktopDatabase
from storage.project_repository import ProjectRepository

MIGRATION_KEY = "legacy_sessions_migrated"


def migrate_legacy_sessions(database: DesktopDatabase, sessions_dir: Path) -> None:
    if database.metadata_get(MIGRATION_KEY) == "1":
        return
    if not sessions_dir.exists():
        database.metadata_set(MIGRATION_KEY, "1")
        return

    repository = ProjectRepository(database)
    for session_path in sorted(sessions_dir.iterdir()):
        if not session_path.is_dir() or session_path.name.startswith("."):
            continue

        project_id = session_path.name
        repository.ensure_project(project_id)

        tasks_path = session_path / "tasks.json"
        if tasks_path.exists():
            payload = json.loads(tasks_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                repository.save_tasks_payload(project_id, payload)

        conversation_path = session_path / "conversation.json"
        if conversation_path.exists():
            messages = json.loads(conversation_path.read_text(encoding="utf-8"))
            if isinstance(messages, list):
                repository.save_conversation(project_id, messages)

    database.metadata_set(MIGRATION_KEY, "1")
