"""Base workflow expansion projector and shared read helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from engine.graph.assumption_checker import field_value
from engine.graph.graph_engine import normalize_root_id
from engine.graph.graph_store import GraphStore
from engine.reference.graph_db import GraphEdgeRecord, GraphNodeRecord
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskNotFoundError
from engine.state.task_facts import active_facts
from models.fact import Fact, ValidationStatus, fact_scalar_value
from models.planning import NavigationPhase
from models.task import Task, TaskStatus

from dev.graph_explorer.adapter import GraphExplorerAdapter, TaskContextReader
from dev.graph_explorer.expansion_types import (
    DEPENDENCY_EDGE_TYPES,
    PIPE_WALL_PHASE_FIELDS,
    PIPE_WALL_TIMELINE_PHASES,
    REFERENCE_EDGE_TYPES,
)


def load_task_for_graph_explorer(
    adapter: GraphExplorerAdapter,
    task_id: str | None,
    session_id: str | None = None,
) -> Task | None:
    """Load full Task object from session storage."""
    sid = session_id or adapter.session_id
    reader = adapter._reader(sid)
    from storage.migrate_legacy_sessions import migrate_legacy_sessions
    from storage.project_repository import ProjectRepository
    from storage.project_session_store import ProjectSessionStore, get_database_for_config

    db = get_database_for_config(reader.config.sessions_dir)
    migrate_legacy_sessions(db, reader.config.sessions_dir)
    repository = ProjectRepository(db)
    if repository.get_project(sid) is None:
        repository.ensure_project(sid)
    store = ProjectSessionStore(db, reader.config.sessions_dir, session_id=sid)
    manager = store.load_state_manager()
    if not task_id:
        active = manager.get_active_task()
        if active is None:
            tasks = manager.list_tasks()
            if not tasks:
                return None
            return tasks[-1]
        return active
    try:
        return manager.get_task(task_id)
    except TaskNotFoundError:
        return None


def resolve_workflow_id(task: Task) -> str:
    outputs = task.outputs if isinstance(task.outputs, dict) else {}
    for key in ("workflow", "selected_root", "graph_root"):
        value = outputs.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_root_id(value.strip())
    return ""


def extract_task_inputs(task: Task) -> dict[str, dict[str, Any]]:
    """Map active facts to visualization-friendly input records."""
    result: dict[str, dict[str, Any]] = {}
    for key, fact in active_facts(task).items():
        value = fact_scalar_value(fact)
        status = "confirmed"
        if fact.validation.status == ValidationStatus.PENDING or fact.requires_confirmation:
            status = "pending"
        elif fact.validation.status == ValidationStatus.REJECTED:
            status = "invalid"
        source = "user"
        if fact.fact_class is not None:
            source = str(fact.fact_class.value)
        elif fact.provenance.created_by:
            source = str(fact.provenance.created_by)
        result[key] = {"value": value, "status": status, "source": source}
    return result


def extract_planning_summary(task: Task, inputs: dict[str, Fact]) -> dict[str, Any]:
    """Planning-compatible summary from goals, legacy outputs, or inference."""
    if task.goal_store.goals:
        summary: dict[str, Any] = dict(planning_projection(task))
    else:
        legacy = task.outputs.get("planning_summary")
        summary = dict(legacy) if isinstance(legacy, dict) else {}

    for key in (
        "path_decision",
        "selected_nodes",
        "selected_root",
        "active_definition_node",
        "phase_allowed_fields",
        "graph_input_order",
        "graph_step_titles",
    ):
        if task.outputs.get(key) is not None:
            summary[key] = task.outputs[key]

    if not summary.get("current_phase"):
        summary["current_phase"] = infer_current_phase(inputs)
    if not summary.get("phase_missing"):
        summary["phase_missing"] = infer_phase_missing(inputs, str(summary.get("current_phase") or ""))
    if not summary.get("intent") and task.outputs.get("workflow"):
        summary["intent"] = task.outputs.get("workflow")
    return summary


def extract_execution_trace(task: Task) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    trace = task.outputs.get("_execution_trace")
    skipped = task.outputs.get("_skipped_trace")
    execution = [item for item in trace if isinstance(item, dict)] if isinstance(trace, list) else []
    skipped_items = [item for item in skipped if isinstance(item, dict)] if isinstance(skipped, list) else []
    return execution, skipped_items


def get_input_value(inputs: dict[str, Fact], input_id: str) -> Any:
    return field_value(input_id, inputs)


def infer_current_phase(inputs: dict[str, Fact]) -> str:
    """Infer navigation phase from gate and parameter facts."""
    straight = field_value("straight_pipe_section", inputs)
    if straight is None:
        return NavigationPhase.EXPANSION_ASSUMPTIONS.value
    if straight is False:
        return NavigationPhase.EXPANSION_ASSUMPTIONS.value

    pressure = field_value("pressure_loading", inputs)
    if pressure is None:
        return NavigationPhase.PATH_DECISIONS.value

    for phase in PIPE_WALL_TIMELINE_PHASES:
        if phase == NavigationPhase.PATH_DECISIONS.value:
            continue
        fields = PIPE_WALL_PHASE_FIELDS.get(phase, ())
        if not fields:
            continue
        if any(field_value(field_name, inputs) is None for field_name in fields):
            return phase

    corrosion = field_value("corrosion_allowance", inputs)
    if corrosion is None:
        return NavigationPhase.DEFINITION_EQUATION_COMPLETION.value

    return NavigationPhase.READY.value


def infer_phase_missing(inputs: dict[str, Fact], current_phase: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    started = False
    for phase in PIPE_WALL_TIMELINE_PHASES + (NavigationPhase.DEFINITION_EQUATION_COMPLETION.value,):
        fields = PIPE_WALL_PHASE_FIELDS.get(phase, ())
        missing = [name for name in fields if field_value(name, inputs) is None]
        if missing:
            result[phase] = missing
        if phase == current_phase:
            started = True
        elif not started and phase != NavigationPhase.EXPANSION_ASSUMPTIONS.value:
            continue
    return result


def task_status_label(task: Task) -> str:
    try:
        return task.status.value
    except Exception:
        return "unknown"


def node_label(record: GraphNodeRecord | None, node_id: str) -> str:
    if record is None:
        return node_id
    meta = record.metadata
    for key in ("title", "symbol", "display_heading", "name"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    paragraph = meta.get("paragraph") or meta.get("paragraph_number")
    if isinstance(paragraph, str) and paragraph.strip():
        return f"§{paragraph.strip()}"
    return node_id


def node_graph_type(record: GraphNodeRecord | None, node_id: str) -> str:
    if record is None:
        return "unknown"
    node_type = record.node_type or "unknown"
    kind = record.metadata.get("kind")
    mode = record.metadata.get("mode")
    if node_type == "parameter":
        return "parameter"
    if node_type == "workflow":
        return "workflow"
    if node_type in {"lookup", "table"}:
        return "lookup"
    if node_type == "equation":
        return "equation"
    if node_type == "text":
        return "text"
    if mode == "decision" or kind == "interaction":
        return "interaction"
    if node_type in {"paragraph", "definition"}:
        return "definition"
    if node_type in {"calculation", "equation"}:
        return "calculation"
    return node_type


def trace_by_node_id(trace: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in trace:
        node_id = str(item.get("node_id", ""))
        if node_id:
            result[node_id] = item
    return result


def execution_status_map(trace: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in trace:
        node_id = str(item.get("node_id", ""))
        if not node_id:
            continue
        raw = str(item.get("status", ""))
        if raw == "completed":
            mapping[node_id] = "executed"
        elif raw == "error":
            mapping[node_id] = "failed"
        elif raw == "skipped":
            mapping[node_id] = "skipped"
        elif raw == "awaiting_input":
            mapping[node_id] = "awaiting_input"
        else:
            mapping[node_id] = raw or "unknown"
    return mapping


class ExpansionProjector(ABC):
    """Build visualization-ready workflow expansion JSON for a task."""

    def __init__(self, adapter: GraphExplorerAdapter) -> None:
        self.adapter = adapter

    def find_store(self, node_id: str) -> GraphStore | None:
        slug = self.adapter._node_pack.get(node_id)  # noqa: SLF001
        if slug:
            return self.adapter._stores.get(slug)  # noqa: SLF001
        for store in self.adapter._stores.values():  # noqa: SLF001
            if store.get_node(node_id) is not None:
                return store
        return None

    def find_node(self, node_id: str) -> tuple[GraphNodeRecord | None, GraphStore | None]:
        record = self.adapter._find_node(node_id)  # noqa: SLF001
        if record is None:
            return None, None
        return record, self.find_store(record.node_id)

    def resolve_id(self, store: GraphStore | None, node_id: str) -> str:
        if store is None:
            return node_id
        return store.resolve_node_id(node_id) or node_id

    @abstractmethod
    def project(self, task: Task, *, requested_task_id: str | None = None) -> dict[str, Any]:
        """Return workflow expansion view dict."""


class GenericExpansionProjector(ExpansionProjector):
    """Fallback projector: active_nodes subgraph with trace overlay."""

    def project(self, task: Task, *, requested_task_id: str | None = None) -> dict[str, Any]:
        warnings: list[str] = []
        workflow = resolve_workflow_id(task) or "unknown"
        inputs = active_facts(task)
        planning = extract_planning_summary(task, inputs)
        execution_trace, skipped_trace = extract_execution_trace(task)
        exec_status = execution_status_map(execution_trace)

        if not self.adapter._stores:  # noqa: SLF001
            warnings.append("No compiled graph databases available.")

        visible = set(task.active_nodes)
        for item in execution_trace:
            node_id = str(item.get("node_id", ""))
            if node_id:
                visible.add(node_id)

        nodes: list[dict[str, Any]] = []
        for node_id in sorted(visible):
            record, _store = self.find_node(node_id)
            status = exec_status.get(node_id, "active" if node_id in task.active_nodes else "unknown")
            nodes.append(
                {
                    "id": node_id,
                    "label": node_label(record, node_id),
                    "type": node_graph_type(record, node_id),
                    "status": status,
                    "visible": True,
                    "active": node_id in task.active_nodes,
                    "blocked": False,
                    "skipped": status == "skipped",
                    "reason": f"Present in task.active_nodes ({status})",
                    "missing_inputs": [],
                    "provided_outputs": [],
                    "required_inputs": [],
                    "phase": str(planning.get("current_phase") or "unknown"),
                    "details": {
                        "source": "task_state" if node_id in task.active_nodes else "execution_trace",
                    },
                }
            )

        edges = self._edges_for_nodes(visible, exec_status)
        return {
            "task_id": task.task_id,
            "workflow": workflow,
            "task_status": task_status_label(task),
            "current_phase": str(planning.get("current_phase") or "unknown"),
            "phase_missing": planning.get("phase_missing") or {},
            "inputs": extract_task_inputs(task),
            "expansion_state": {},
            "nodes": nodes,
            "edges": edges,
            "timeline": [],
            "warnings": warnings,
            "debug": {
                "has_task": True,
                "has_compiled_graph": bool(self.adapter._stores),  # noqa: SLF001
                "has_planning_summary": bool(task.goal_store.goals or task.outputs.get("planning_summary")),
                "has_execution_trace": bool(execution_trace),
                "projector": "generic",
                "skipped_trace_count": len(skipped_trace),
            },
        }

    def _edges_for_nodes(
        self,
        visible: set[str],
        exec_status: dict[str, str],
    ) -> list[dict[str, Any]]:
        edge_dtos: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for node_id in visible:
            record, store = self.find_node(node_id)
            if store is None:
                continue
            resolved = self.resolve_id(store, node_id)
            for edge in store.outgoing(resolved):
                if edge.to_id not in visible:
                    continue
                key = (edge.from_id, edge.to_id, edge.edge_type)
                if key in seen:
                    continue
                seen.add(key)
                edge_dtos.append(self._edge_dict(edge, exec_status))
            for edge in store.incoming(resolved):
                if edge.from_id not in visible:
                    continue
                key = (edge.from_id, edge.to_id, edge.edge_type)
                if key in seen:
                    continue
                seen.add(key)
                edge_dtos.append(self._edge_dict(edge, exec_status))
        return edge_dtos

    @staticmethod
    def _edge_dict(edge: GraphEdgeRecord, exec_status: dict[str, str]) -> dict[str, Any]:
        edge_type = "reference" if edge.edge_type in REFERENCE_EDGE_TYPES else "dependency"
        if edge.edge_type in DEPENDENCY_EDGE_TYPES:
            edge_type = "active" if exec_status.get(edge.from_id) == "executed" else "dependency"
        when = edge.metadata.get("when") if edge.metadata else None
        condition = ""
        if isinstance(when, dict):
            edge_type = "conditional"
            field_name = when.get("field", "")
            allowed = when.get("in") or []
            condition = f"{field_name} in {allowed}"
        return {
            "id": f"{edge.from_id}->{edge.to_id}",
            "source": edge.from_id,
            "target": edge.to_id,
            "type": edge_type,
            "active": exec_status.get(edge.from_id) == "executed",
            "skipped": False,
            "reason": condition or edge.edge_type,
            "condition": condition,
        }
