"""Tests for SQLite desktop storage."""

from __future__ import annotations

import json
from pathlib import Path

from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from storage.desktop_database import DesktopDatabase
from storage.migrate_legacy_sessions import migrate_legacy_sessions
from storage.project_repository import ProjectRepository
from storage.project_session_store import ProjectSessionStore


def test_project_repository_create_and_list(tmp_path: Path) -> None:
    database = DesktopDatabase(tmp_path / "desktop.db")
    repository = ProjectRepository(database)

    created = repository.create_project("Refinery Expansion")
    projects = repository.list_projects()

    assert created["name"] == "Refinery Expansion"
    assert any(project["id"] == created["id"] for project in projects)


def test_project_session_store_persists_tasks(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    database = DesktopDatabase(tmp_path / "desktop.db")
    repository = ProjectRepository(database)
    repository.ensure_project("project-a")
    store = ProjectSessionStore(database, sessions_dir, session_id="project-a")

    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-store01", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    manager.replace_task(task.task_id, task)
    store.save_state_manager(manager)

    reloaded = ProjectSessionStore(database, sessions_dir, session_id="project-a")
    restored = reloaded.load_state_manager().get_task(task.task_id)
    assert restored.outputs["workflow"] == "pipe_wall_thickness_design"


def test_legacy_session_migration_imports_json(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    legacy = sessions_dir / "legacy-project"
    legacy.mkdir(parents=True)
    (legacy / "reports").mkdir()

    payload = {
        "active_task_id": "pipe-wall-thickness-desi-legacy1",
        "tasks": [
            {
                "task_id": "pipe-wall-thickness-desi-legacy1",
                "status": "awaiting_input",
                "active_nodes": [],
                "inputs": {},
                "outputs": {"workflow": "pipe_wall_thickness_design"},
                "warnings": [],
                "conflicts": [],
            }
        ],
    }
    (legacy / "tasks.json").write_text(json.dumps(payload), encoding="utf-8")
    (legacy / "conversation.json").write_text(
        json.dumps([{"role": "user", "content": "hello", "timestamp": "2026-01-01T00:00:00+00:00"}]),
        encoding="utf-8",
    )

    database = DesktopDatabase(tmp_path / "desktop.db")
    migrate_legacy_sessions(database, sessions_dir)

    repository = ProjectRepository(database)
    project = repository.get_project("legacy-project")
    assert project is not None
    assert project["task_count"] == 1
    assert len(repository.load_conversation("legacy-project")) == 1
