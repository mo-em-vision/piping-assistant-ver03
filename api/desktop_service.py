"""Desktop application REST API service layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cli.session_store import new_task_id
from config.loader import CLIConfig
from engine.router import PIPE_WALL_THICKNESS_DESIGN, Router
from engine.state.state_manager import TaskNotFoundError, TaskStateManager
from models.task import TaskStatus
from storage.migrate_legacy_sessions import migrate_legacy_sessions
from storage.project_repository import ProjectRepository
from storage.project_session_store import ProjectSessionStore, get_database_for_config, list_project_summaries

from api.chat_service import list_chat_messages, send_chat_message
from api.report_service import (
    generate_task_report,
    get_report_preview,
    get_report_status,
    resolve_report_download,
)
from api.parameter_definitions import submit_task_input
from api.material_catalog import search_astm_materials
from api.serializers import task_state, task_summary, workflow_catalog


class ApiError(Exception):
    def __init__(self, code: str, message: str, *, status: int = 400, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


@dataclass
class DesktopApiService:
    config: CLIConfig
    session_id: str = "default"

    @classmethod
    def from_project_root(cls, project_root: Path | None = None) -> DesktopApiService:
        root = project_root or Path(__file__).resolve().parent.parent
        service = cls(config=CLIConfig.load(project_root=root))
        service._ensure_storage()
        return service

    def _ensure_storage(self) -> None:
        migrate_legacy_sessions(self._database(), self.config.sessions_dir)
        ProjectRepository(self._database()).ensure_project(self.session_id)

    def _database(self):
        return get_database_for_config(self.config.sessions_dir)

    def _store(self) -> ProjectSessionStore:
        return ProjectSessionStore(self._database(), self.config.sessions_dir, session_id=self.session_id)

    def _load_manager(self) -> TaskStateManager:
        return self._store().load_state_manager()

    def _save_manager(self, manager: TaskStateManager, session_id: str | None = None) -> None:
        self._store_for(session_id).save_state_manager(manager)

    def list_workflows(self) -> list[dict[str, Any]]:
        return workflow_catalog()

    def list_projects(self) -> list[dict[str, Any]]:
        self._ensure_storage()
        repository = ProjectRepository(self._database())
        repository.ensure_project(self.session_id)
        projects = list_project_summaries(self._database())
        if not projects:
            repository.ensure_project(self.session_id, name="Default Project")
            projects = list_project_summaries(self._database())
        return projects

    def get_project(self, project_id: str) -> dict[str, Any]:
        self._ensure_storage()
        project = ProjectRepository(self._database()).get_project(project_id)
        if project is None:
            raise ApiError("project_not_found", f"Project not found: {project_id}", status=404)
        return {
            "id": project["id"],
            "name": project["name"],
            "task_count": int(project["task_count"] or 0),
            "updated_at": project["updated_at"],
            "active_task_id": project.get("active_task_id"),
        }

    def create_project(self, name: str) -> dict[str, Any]:
        cleaned = name.strip()
        if not cleaned:
            raise ApiError("invalid_request", "name is required", status=400)
        self._ensure_storage()
        project = ProjectRepository(self._database()).create_project(cleaned)
        session_path = self.config.sessions_dir / project["id"]
        session_path.mkdir(parents=True, exist_ok=True)
        (session_path / "reports").mkdir(exist_ok=True)
        return {
            "id": project["id"],
            "name": project["name"],
            "task_count": int(project["task_count"] or 0),
            "updated_at": project["updated_at"],
            "active_task_id": project.get("active_task_id"),
        }

    def activate_project(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        return {
            "project": project,
            "session_id": project["id"],
        }

    def list_tasks(self, session_id: str | None = None) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        active = manager.get_active_task()
        tasks = [task_summary(task) for task in manager.list_tasks()]
        recent = [
            task_summary(task)
            for task in store.incomplete_tasks(manager)
            if task.status != TaskStatus.COMPLETED
        ]
        return {
            "session_id": store.session_id,
            "active_task_id": active.task_id if active else None,
            "tasks": tasks,
            "recent_tasks": recent,
        }

    def get_task(self, task_id: str, session_id: str | None = None) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            task = manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        return task_state(task, manager)

    def create_task(self, workflow_id: str, session_id: str | None = None) -> dict[str, Any]:
        router = Router()
        if workflow_id not in router.supported_workflows():
            raise ApiError(
                "workflow_unavailable",
                f"Workflow is not available: {workflow_id}",
                status=400,
                details={"workflow_id": workflow_id},
            )

        store = self._store_for(session_id)
        manager = store.load_state_manager()
        task_id = new_task_id(workflow_id)
        task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        task.outputs["workflow"] = workflow_id
        task.outputs["selected_root"] = workflow_id
        if workflow_id == PIPE_WALL_THICKNESS_DESIGN:
            task.outputs["planning_summary"] = {
                "goal": "pipe wall thickness design",
                "intent": workflow_id,
                "selected_root": workflow_id,
                "selected_nodes": [],
                "missing_assumptions": ["pressure_loading"],
                "missing_execution_assumptions": ["pressure_loading"],
                "missing_inputs": ["material", "design_pressure", "design_temperature"],
                "path_decision": None,
                "confidence": 1.0,
                "action": "request_input",
            }
        manager.replace_task(task_id, task)
        self._save_manager(manager, session_id)
        return task_state(task, manager)

    def activate_task(self, task_id: str, session_id: str | None = None) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            task = manager.set_active_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        self._save_manager(manager, session_id)
        return task_state(task, manager)

    def submit_input(
        self,
        task_id: str,
        *,
        parameter: str,
        value: Any,
        unit: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc

        try:
            task = submit_task_input(
                manager,
                task_id,
                parameter=parameter,
                value=value,
                unit=unit,
            )
        except ValueError as exc:
            raise ApiError(
                "invalid_input",
                str(exc),
                status=400,
                details={"parameter": parameter},
            ) from exc

        self._save_manager(manager, session_id)
        return task_state(task, manager)

    def list_chat_messages(self, session_id: str | None = None) -> dict[str, Any]:
        store = self._store_for(session_id)
        return {
            "session_id": store.session_id,
            "messages": list_chat_messages(store),
        }

    def post_chat_message(
        self,
        message: str,
        *,
        task_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            return send_chat_message(
                store,
                self.config,
                manager,
                message=message,
                task_id=task_id,
            )
        except ValueError as exc:
            raise ApiError("invalid_request", str(exc), status=400) from exc

    def get_task_report(self, task_id: str, session_id: str | None = None) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        return get_report_status(store, self.config, manager, task_id)

    def generate_task_report(
        self,
        task_id: str,
        *,
        report_format: str = "html",
        with_ai: bool = False,
        draft: bool = False,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        try:
            return generate_task_report(
                store,
                self.config,
                manager,
                task_id,
                report_format=report_format,
                with_ai=with_ai,
                draft=draft,
            )
        except ValueError as exc:
            raise ApiError("invalid_request", str(exc), status=400) from exc

    def preview_task_report(
        self,
        task_id: str,
        *,
        preview_format: str = "html",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        try:
            return get_report_preview(
                store,
                self.config,
                manager,
                task_id,
                preview_format=preview_format,
            )
        except ValueError as exc:
            raise ApiError("invalid_request", str(exc), status=400) from exc

    def download_task_report(
        self,
        task_id: str,
        *,
        download_format: str,
        session_id: str | None = None,
    ) -> tuple[Path, str]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        try:
            return resolve_report_download(store, task_id, download_format=download_format)
        except ValueError as exc:
            raise ApiError("invalid_request", str(exc), status=400) from exc
        except FileNotFoundError as exc:
            raise ApiError("report_not_found", str(exc), status=404) from exc

    def search_materials(self, query: str) -> dict[str, Any]:
        materials = search_astm_materials(self.config.standards_root, query)
        return {"materials": materials, "query": query}

    def _store_for(self, session_id: str | None) -> ProjectSessionStore:
        resolved = session_id or self.session_id
        return ProjectSessionStore(self._database(), self.config.sessions_dir, session_id=resolved)


def _session_updated_at(store: ProjectSessionStore) -> str:
    project = store.repository.get_project(store.session_id)
    return str(project["updated_at"]) if project else ""
