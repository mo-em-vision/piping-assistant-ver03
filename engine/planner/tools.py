"""Planner layer tools — graph, state, and rule access."""

from __future__ import annotations

from typing import Any

from engine.graph.graph_engine import GraphEngine, normalize_root_id
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.agent import AlternativePathRecord
from models.execution import ExecutionPlan
from models.input import EngineeringInput
from models.planning import WorkflowCandidate
from models.task import Task


class GraphTools:
    """Graph Engine wrappers for planner discovery and preview."""

    def __init__(self, reader: StandardsReader) -> None:
        self._reader = reader
        self._engine = GraphEngine()

    def discover_roots(
        self,
        *,
        workflow: str | None = None,
        keywords: list[str] | None = None,
    ) -> list[WorkflowCandidate]:
        return self._engine.discover_roots(
            self._reader,
            workflow=workflow,
            keywords=keywords,
        )

    def normalize_root_id(self, root_ref: str) -> str:
        return normalize_root_id(root_ref)

    def required_user_inputs(
        self,
        root_id: str,
        *,
        existing_inputs: set[str] | None = None,
    ) -> list[str]:
        return self._engine.required_user_inputs(
            root_id,
            self._reader,
            existing_inputs=existing_inputs,
        )

    def preview_plan(
        self,
        *,
        task_id: str,
        root_id: str,
        inputs: dict[str, EngineeringInput] | None = None,
    ) -> ExecutionPlan:
        slug = normalize_root_id(root_id)
        return self._engine.build_plan(
            task_id=task_id,
            root_id=slug,
            inputs=inputs or {},
            reader=self._reader,
        )

    def limitation_hints(self, node_ids: list[str]) -> list[str]:
        hints: list[str] = []
        for node_id in node_ids:
            record = self._reader.load(node_id)
            for item in record.metadata.get("limitations", []) or []:
                if isinstance(item, dict):
                    condition = str(item.get("condition", ""))
                    if condition:
                        hints.append(condition)
        return hints


class StateTools:
    """Task state read/write for planner decisions."""

    def __init__(self, state: TaskStateManager) -> None:
        self._state = state

    def get_task(self, task_id: str) -> Task:
        return self._state.get_task(task_id)

    def persist_planning(
        self,
        task_id: str,
        *,
        workflow: str | None,
        selected_root: str | None,
        active_nodes: list[str],
        planning_summary: dict[str, Any],
    ) -> Task:
        task = self._state.get_task(task_id)
        if workflow:
            self._state.store_output(task_id, "workflow", workflow)
        if selected_root:
            self._state.store_output(task_id, "selected_root", selected_root)
        self._state.set_active_nodes(task_id, active_nodes)
        self._state.store_output(task_id, "planning_summary", planning_summary)
        return task

    def record_alternative_path(
        self,
        task_id: str,
        *,
        selected: str,
        alternative: str,
        reason: str | None = None,
    ) -> None:
        task = self._state.get_task(task_id)
        paths = list(task.outputs.get("alternative_paths", []))
        paths.append(
            AlternativePathRecord(
                selected=selected,
                alternative=alternative,
                reason=reason,
            ).__dict__
        )
        self._state.store_output(task_id, "alternative_paths", paths)


class RuleTools:
    """Read-only rule/limitation hints for the planner (no validation execution)."""

    def __init__(self, reader: StandardsReader) -> None:
        self._reader = reader

    def limitation_hints(self, node_ids: list[str]) -> list[str]:
        hints: list[str] = []
        for node_id in node_ids:
            record = self._reader.load(node_id)
            for item in record.metadata.get("limitations", []) or []:
                if isinstance(item, dict):
                    condition = str(item.get("condition", ""))
                    if condition:
                        hints.append(condition)
        return hints
