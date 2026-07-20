"""Desktop application REST API service layer."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from storage.session_store import new_task_id, _task_from_dict
from config.loader import CLIConfig
from engine.graph.graph_engine import GraphEngine
from engine.reference.standards_reader import StandardsReader
from engine.router import Router
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskNotFoundError, TaskStateManager
from models.task import TaskStatus
from storage.migrate_legacy_sessions import migrate_legacy_sessions
from storage.project_repository import ProjectRepository
from storage.project_session_store import ProjectSessionStore, get_database_for_config, list_project_summaries

from api.chat_service import list_chat_messages, send_chat_message, clear_chat_messages
from api.report_service import (
    generate_task_report,
    get_report_preview,
    get_report_status,
    resolve_report_download,
)
from api.parameter_definitions import submit_task_input
from api.node_context import node_source_payload, subsection_source_payload
from api.table_context import table_source_payload
from api.standards_browse import build_standards_browse_payload, resolve_browse_standard
from api.workflow_bootstrap import (
    bootstrap_new_task,
    ensure_task_planning,
    maybe_execute_ready_workflow,
    refresh_task_planning,
    standards_reader_for_config,
    task_ready_for_execution,
)
from engine.graph.definition_equations import (
    has_execution_trace,
    try_complete_definition_equations,
)
from engine.planner.tools import GraphTools
from api.material_catalog import search_astm_materials, warm_astm_material_catalog
from api.material_detail import get_material_detail as resolve_material_detail
from api.parameter_edit import (
    assess_parameter_edit,
    begin_parameter_edit as begin_parameter_edit_session,
)
from api.serializers import task_state, task_summary, workflow_catalog
from api.completion_next_workflows_transcript import (
    append_completion_next_workflows_transcript,
    flatten_transcript_blocks_for_api,
    maybe_repair_completion_next_workflows_transcript,
)
from api.flow_guidance_sync import sync_flow_guidance_transcript
from api.input_archive_transcript import InputArchiveEvent, append_input_archive_transcript
from api.engineering_decision_transcript import (
    EngineeringDecisionEvent,
    append_engineering_decision_transcript,
    latest_decision_for_key,
)
from engine.messaging.decision_interaction_resolver import is_node_owned_decision_key
from engine.state.decision_recorder import record_decision_from_fact
from api.task_continuation_service import get_continuation_suggestions
from engine.planner.goal_navigation import build_current_ask
from engine.reference.parameter_keys import canonical_parameter_key
from engine.inspection.performance_trace import attach_trace_to_payload, perf_span

_PROPOSE_DEFAULTS_ON_FIELDS = frozenset(
    {
        "material_grade",
        "design_temperature",
        "nominal_pipe_size",
        "outside_diameter",
        "pipe_construction_type",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
        "corrosion_allowance",
    }
)


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
    _standards_reader: StandardsReader | None = field(default=None, init=False, repr=False)

    def _reader(self) -> StandardsReader:
        if self._standards_reader is None:
            self._standards_reader = standards_reader_for_config(self.config)
        return self._standards_reader

    def _task_state(self, task, manager) -> dict[str, Any]:
        payload = task_state(
            task,
            manager,
            standards_root=self.config.standards_root,
            reader=self._reader(),
            projection_mode="interactive",
        )
        with perf_span("performance_trace_attachment", "serializer"):
            return attach_trace_to_payload(payload)

    def _maybe_ensure_task_planning(self, task, manager):
        reader = self._reader()
        if ensure_task_planning(task, reader):
            manager.replace_task(task.task_id, task)
            return task, True
        return task, False

    def _maybe_refresh_post_execution_task(self, task, manager):
        from engine.graph.definition_equations import has_execution_trace, pending_definition_equation_inputs
        from engine.graph.graph_engine import GraphEngine, normalize_root_id
        from engine.planner.workflow_goal_metadata import goal_output_value_for_task

        task, changed = self._maybe_ensure_task_planning(task, manager)
        if not has_execution_trace(task) and task_ready_for_execution(task):
            task = maybe_execute_ready_workflow(task.task_id, manager, self._reader())
            changed = True
        if not has_execution_trace(task):
            return task, changed

        workflow = normalize_root_id(str(task.outputs.get("workflow") or task.outputs.get("selected_root") or ""))
        if workflow.startswith("B313-"):
            selected = normalize_root_id(str(task.outputs.get("selected_root") or ""))
            if selected and selected != workflow:
                task.outputs["workflow"] = selected
                changed = True

        if goal_output_value_for_task(task) is None:
            return task, changed

        reader = self._reader()
        preview = GraphEngine().build_plan(
            task_id=task.task_id,
            root_id=workflow,
            inputs=dict(task.fact_store.active_facts()),
            reader=reader,
        )
        pending = pending_definition_equation_inputs(task, reader, preview.execution_order)
        planning = planning_projection(task)
        phase = planning.get("current_phase")
        needs_refresh = bool(pending) and (
            task.status != TaskStatus.COMPLETED
            or phase != "definition_equation_completion"
        )
        if needs_refresh:
            refresh_task_planning(task, reader)
            manager.replace_task(task.task_id, task)
            changed = True
        return task, changed

    def _prepare_task_for_projection(self, task, manager) -> tuple[Any, bool]:
        task, refresh_changed = self._maybe_refresh_post_execution_task(task, manager)
        task, transcript_changed = sync_flow_guidance_transcript(task, self._reader())
        if transcript_changed:
            manager.replace_task(task.task_id, task)
        keys_changed = self._sync_equation_display_registry(task)
        if keys_changed:
            manager.replace_task(task.task_id, task)
            task = manager.get_task(task.task_id)
        repair_changed = False
        if task.status == TaskStatus.COMPLETED:
            task, repair_changed = maybe_repair_completion_next_workflows_transcript(
                task,
                self._reader(),
            )
            if repair_changed:
                manager.replace_task(task.task_id, task)
        return task, refresh_changed or transcript_changed or keys_changed or repair_changed

    def _sync_equation_display_registry(self, task) -> bool:
        from api.equation_display_registry import discover_equation_display_entries
        from engine.state.goal_projection import planning_projection

        before = list(task.outputs.get("_equation_trace_keys") or [])
        discover_equation_display_entries(task, self._reader(), planning_projection(task))
        after = list(task.outputs.get("_equation_trace_keys") or [])
        return before != after

    @classmethod
    def from_project_root(cls, project_root: Path | None = None) -> DesktopApiService:
        root = project_root or Path(__file__).resolve().parent.parent
        service = cls(config=CLIConfig.load(project_root=root))
        service._ensure_storage()
        warm_astm_material_catalog(service.config.standards_root)
        return service

    def _ensure_storage(self) -> None:
        migrate_legacy_sessions(self._database(), self.config.sessions_dir)

    def _database(self):
        return get_database_for_config(self.config.sessions_dir)

    def _store(self) -> ProjectSessionStore:
        return ProjectSessionStore(self._database(), self.config.sessions_dir, session_id=self.session_id)

    def _load_manager(self) -> TaskStateManager:
        return self._store().load_state_manager()

    def _save_manager(self, manager: TaskStateManager, session_id: str | None = None) -> None:
        with perf_span("task_state_persist", "database"):
            self._store_for(session_id).save_state_manager(manager)

    def list_workflows(self) -> list[dict[str, Any]]:
        return workflow_catalog(self._reader())

    def get_graph_neighbors(self, node_id: str, *, depth: int = 1) -> dict[str, Any]:
        reader = self._reader()
        levels = GraphEngine().get_neighbors(reader, node_id, depth=depth)
        return {"node_id": node_id, "depth": depth, "levels": levels}

    def list_projects(self) -> list[dict[str, Any]]:
        self._ensure_storage()
        return list_project_summaries(self._database())

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

    def delete_project(self, project_id: str) -> dict[str, Any]:
        if project_id == "default":
            raise ApiError(
                "invalid_request",
                "The default project cannot be deleted",
                status=400,
            )
        self._ensure_storage()
        repository = ProjectRepository(self._database())
        if not repository.delete_project(project_id):
            raise ApiError("project_not_found", f"Project not found: {project_id}", status=404)
        session_path = self.config.sessions_dir / project_id
        if session_path.exists():
            shutil.rmtree(session_path, ignore_errors=True)
        return {
            "id": project_id,
            "deleted": True,
        }

    def rename_project(self, project_id: str, name: str) -> dict[str, Any]:
        cleaned = name.strip()
        if not cleaned:
            raise ApiError("invalid_request", "name is required", status=400)
        self._ensure_storage()
        project = ProjectRepository(self._database()).update_project_name(project_id, cleaned)
        if project is None:
            raise ApiError("project_not_found", f"Project not found: {project_id}", status=404)
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

    def list_recent_tasks_global(self) -> dict[str, Any]:
        self._ensure_storage()
        rows = ProjectRepository(self._database()).list_recent_tasks()
        recent_tasks: list[dict[str, Any]] = []
        for row in rows:
            task = _task_from_dict(json.loads(row["task_json"]))
            summary = task_summary(task)
            summary["project_id"] = row["project_id"]
            summary["project_name"] = row["project_name"]
            recent_tasks.append(summary)
        return {"recent_tasks": recent_tasks}

    def get_task(self, task_id: str, session_id: str | None = None) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            task = manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        task, dirty = self._prepare_task_for_projection(task, manager)
        if dirty:
            self._save_manager(manager, session_id)
        return self._task_state(task, manager)

    def get_workflow_state(self, task_id: str, session_id: str | None = None) -> dict[str, Any]:
        from api.serializers import workflow_state_payload

        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        return workflow_state_payload(manager, task_id, reader=self._reader())

    def get_inspection(self, task_id: str, session_id: str | None = None) -> dict[str, Any]:
        from api.inspection import get_inspection_payload

        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        with perf_span("get_inspection", "api", notes=f"task_id={task_id}"):
            return get_inspection_payload(manager, task_id, reader=self._reader())

    def set_inspection_breakpoint(
        self,
        task_id: str,
        *,
        session_id: str | None = None,
        paused: bool = False,
        step: bool = False,
    ) -> dict[str, Any]:
        from api.inspection import set_breakpoint

        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        payload = set_breakpoint(manager, task_id, paused=paused, step=step)
        self._save_manager(manager, session_id)
        return payload

    def run_inspection_integrity(self, session_id: str | None = None) -> dict[str, Any]:
        from api.inspection import run_integrity

        return run_integrity(self._reader())

    def get_operations(self) -> dict[str, Any]:
        from api.operation_tracker import get_operations_payload

        return get_operations_payload()

    def create_task(self, workflow_id: str, session_id: str | None = None) -> dict[str, Any]:
        with perf_span("create_task", "api", notes=f"workflow_id={workflow_id}"):
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
            bootstrap_new_task(task, workflow_id, self.config)
            manager.replace_task(task_id, task)
            task, _dirty = self._prepare_task_for_projection(task, manager)
            self._save_manager(manager, session_id)
            return self._task_state(task, manager)

    def activate_task(self, task_id: str, session_id: str | None = None) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            task = manager.set_active_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        task, dirty = self._prepare_task_for_projection(task, manager)
        if dirty:
            self._save_manager(manager, session_id)
        return self._task_state(task, manager)

    def delete_task(self, task_id: str, session_id: str | None = None) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc

        manager.delete_task(task_id)
        self._save_manager(manager, session_id)
        return {
            "task_id": task_id,
            "deleted": True,
            "session_id": store.session_id,
        }

    def rename_task(self, task_id: str, name: str, session_id: str | None = None) -> dict[str, Any]:
        cleaned = name.strip()
        if not cleaned:
            raise ApiError("invalid_request", "name is required", status=400)
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            task = manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        task.outputs["display_name"] = cleaned
        manager.replace_task(task_id, task)
        task, _dirty = self._prepare_task_for_projection(task, manager)
        self._save_manager(manager, session_id)
        return self._task_state(task, manager)

    def submit_input(
        self,
        task_id: str,
        *,
        parameter: str,
        value: Any,
        unit: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        with perf_span("submit_input", "api", notes=f"parameter={parameter}"):
            store = self._store_for(session_id)
            manager = store.load_state_manager()
            try:
                manager.get_task(task_id)
            except TaskNotFoundError as exc:
                raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc

            task_before = manager.get_task(task_id)
            was_completed = task_before.status == TaskStatus.COMPLETED
            reader = self._reader()
            planning_before = planning_projection(task_before)
            pre_submit_current_ask = build_current_ask(task_before, planning_before, reader=reader)
            canonical_parameter = canonical_parameter_key(parameter)

            try:
                task = submit_task_input(
                    manager,
                    task_id,
                    parameter=parameter,
                    value=value,
                    unit=unit,
                    standards_root=self._reader().standards_root,
                )
            except ValueError as exc:
                raise ApiError(
                    "invalid_input",
                    str(exc),
                    status=400,
                    details={"parameter": parameter},
                ) from exc

            propose_on_field = parameter in _PROPOSE_DEFAULTS_ON_FIELDS
            refresh_task_planning(
                task,
                self._reader(),
                propose_defaults=propose_on_field,
                allow_lightweight_refresh=True,
            )
            manager.replace_task(task_id, task)
            task = maybe_execute_ready_workflow(task_id, manager, self._reader())

            reader = self._reader()
            needs_finalize_planning = propose_on_field
            if has_execution_trace(task):
                graph = GraphTools(reader)
                root_slug = str(task.outputs.get("selected_root") or task.outputs.get("workflow") or "")
                preview = graph.preview_plan(
                    task_id=task_id,
                    root_id=root_slug,
                    inputs=dict(task.fact_store.active_facts()),
                )
                try_complete_definition_equations(task, reader, preview.execution_order)
                manager.replace_task(task_id, task)
                needs_finalize_planning = True

            if needs_finalize_planning:
                refresh_task_planning(
                    task,
                    reader,
                    propose_defaults=False,
                    allow_lightweight_refresh=False,
                )
                manager.replace_task(task_id, task)
            task = manager.get_task(task_id)
            submitted_fact = task.fact_store.active_fact(canonical_parameter)
            decision_key = canonical_parameter
            if canonical_parameter == "outside_diameter" and str(parameter).endswith("__resolution_branch"):
                decision_key = canonical_parameter_key(parameter)
            elif canonical_parameter_key(parameter).endswith("__resolution_branch"):
                decision_key = canonical_parameter_key(parameter)
            if submitted_fact is not None and is_node_owned_decision_key(decision_key):
                from models.fact import fact_scalar_value

                record_decision_from_fact(
                    task,
                    decision_key,
                    fact_scalar_value(submitted_fact),
                    reader=reader,
                    submission_id=str(submitted_fact.id),
                    source_type="resolution_branch" if decision_key.endswith("__resolution_branch") else "user_input",
                )
                manager.replace_task(task_id, task)
                task = manager.get_task(task_id)
            if submitted_fact is not None:
                task, archive_changed = append_input_archive_transcript(
                    task,
                    InputArchiveEvent(
                        pre_submit_current_ask=pre_submit_current_ask,
                        submitted_parameter_id=canonical_parameter,
                        submitted_raw_value=value,
                        submitted_unit=unit,
                        fact=submitted_fact,
                    ),
                )
                if archive_changed:
                    manager.replace_task(task_id, task)
                    task = manager.get_task(task_id)

            if submitted_fact is not None and is_node_owned_decision_key(decision_key):
                decision = latest_decision_for_key(task, decision_key)
                if decision is not None:
                    task, decision_changed = append_engineering_decision_transcript(
                        task,
                        reader,
                        EngineeringDecisionEvent(
                            decision_key=decision_key,
                            decision=decision,
                        ),
                    )
                    if decision_changed:
                        manager.replace_task(task_id, task)
                        task = manager.get_task(task_id)

            if task.status == TaskStatus.COMPLETED and not was_completed:
                task, next_workflows_changed = append_completion_next_workflows_transcript(
                    task,
                    reader,
                )
                if next_workflows_changed:
                    manager.replace_task(task_id, task)
                    task = manager.get_task(task_id)

            task, _dirty = self._prepare_task_for_projection(task, manager)

            self._save_manager(manager, session_id)
            return self._task_state(task, manager)

    def preview_parameter_edit(
        self,
        task_id: str,
        parameter: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            task = manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc

        try:
            return assess_parameter_edit(task, parameter)
        except ValueError as exc:
            raise ApiError(
                "invalid_input",
                str(exc),
                status=400,
                details={"parameter": parameter},
            ) from exc

    def begin_parameter_edit(
        self,
        task_id: str,
        parameter: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            task = manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc

        try:
            begin_parameter_edit_session(task, parameter)
        except ValueError as exc:
            raise ApiError(
                "invalid_input",
                str(exc),
                status=400,
                details={"parameter": parameter},
            ) from exc

        refresh_task_planning(task, self._reader(), propose_defaults=False)
        manager.replace_task(task_id, task)
        task, _dirty = self._prepare_task_for_projection(task, manager)
        self._save_manager(manager, session_id)
        return self._task_state(task, manager)

    def list_chat_messages(
        self,
        session_id: str | None = None,
        *,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        return {
            "session_id": store.session_id,
            "messages": list_chat_messages(store, task_id=task_id),
        }

    def clear_chat_messages(
        self,
        session_id: str | None = None,
        *,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        return clear_chat_messages(store, task_id=task_id)

    def post_chat_message(
        self,
        message: str,
        *,
        display_message: str | None = None,
        task_id: str | None = None,
        mode: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        project_name = None
        try:
            project_name = str(store.repository.get_project(store.session_id).get("name") or "").strip() or None
        except Exception:
            project_name = None
        try:
            return send_chat_message(
                store,
                self.config,
                manager,
                message=message,
                display_message=display_message,
                task_id=task_id,
                mode=mode,
                project_name=project_name,
            )
        except ValueError as exc:
            raise ApiError("invalid_request", str(exc), status=400) from exc

    def _project_name_for_session(self, session_id: str | None = None) -> str | None:
        store = self._store_for(session_id)
        try:
            return str(store.repository.get_project(store.session_id).get("name") or "").strip() or None
        except Exception:
            return None

    def get_task_continuation_suggestions(
        self,
        task_id: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        store = self._store_for(session_id)
        manager = store.load_state_manager()
        try:
            manager.get_task(task_id)
        except TaskNotFoundError as exc:
            raise ApiError("task_not_found", f"Task not found: {task_id}", status=404) from exc
        try:
            return get_continuation_suggestions(
                store,
                self.config,
                manager,
                task_id,
                reader=self._reader(),
                project_name=self._project_name_for_session(session_id),
            )
        except ValueError as exc:
            raise ApiError("task_not_completed", str(exc), status=409) from exc

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

    def warm_material_catalog(self) -> dict[str, Any]:
        return warm_astm_material_catalog(self.config.standards_root)

    def get_material_detail(self, material_id: str) -> dict[str, Any]:
        try:
            return resolve_material_detail(self.config.standards_root, material_id)
        except FileNotFoundError as exc:
            raise ApiError("material_not_found", f"Material not found: {material_id}", status=404) from exc
        except ValueError as exc:
            raise ApiError("material_not_found", str(exc), status=404) from exc

    def get_standards_node(self, node_id: str) -> dict[str, Any]:
        reader = standards_reader_for_config(self.config)
        try:
            return node_source_payload(reader, node_id)
        except FileNotFoundError as exc:
            raise ApiError("node_not_found", f"Node not found: {node_id}", status=404) from exc

    def get_standards_node_subsection(self, node_id: str, subsection_id: str) -> dict[str, Any]:
        reader = standards_reader_for_config(self.config)
        try:
            return subsection_source_payload(reader, node_id, subsection_id)
        except FileNotFoundError as exc:
            raise ApiError("node_not_found", f"Node not found: {node_id}", status=404) from exc
        except KeyError as exc:
            raise ApiError(
                "subsection_not_found",
                f"Subsection not found: {node_id}/{subsection_id}",
                status=404,
            ) from exc

    def get_standards_table(self, table_id: str) -> dict[str, Any]:
        reader = standards_reader_for_config(self.config)
        try:
            return table_source_payload(reader, table_id)
        except FileNotFoundError as exc:
            raise ApiError("table_not_found", f"Table not found: {table_id}", status=404) from exc

    def get_standards_browse(self, standard: str | None = None) -> dict[str, Any]:
        reader = standards_reader_for_config(self.config)
        try:
            resolved = resolve_browse_standard(self.config.standards_root, standard)
            reader = StandardsReader(self.config.standards_root, standard=resolved)
            return build_standards_browse_payload(reader, standard=resolved)
        except FileNotFoundError as exc:
            raise ApiError(
                "standards_browse_unavailable",
                str(exc),
                status=404,
            ) from exc

    def _store_for(self, session_id: str | None) -> ProjectSessionStore:
        if not session_id:
            raise ApiError(
                "project_required",
                "session_id is required",
                status=400,
            )
        project = ProjectRepository(self._database()).get_project(session_id)
        if project is None:
            raise ApiError("project_not_found", f"Project not found: {session_id}", status=404)
        return ProjectSessionStore(self._database(), self.config.sessions_dir, session_id=session_id)


def _session_updated_at(store: ProjectSessionStore) -> str:
    project = store.repository.get_project(store.session_id)
    return str(project["updated_at"]) if project else ""
