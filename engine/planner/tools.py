"""Planner layer tools — graph, state, and rule access."""

from __future__ import annotations

from typing import Any

from engine.graph.assumption_checker import AssumptionEvaluation
from engine.graph.graph_engine import GraphEngine, normalize_root_id
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.agent import AlternativePathRecord
from models.execution import ExecutionPlan
from models.fact import Fact
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
        task_inputs: dict[str, Fact] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> list[str]:
        return self._engine.required_user_inputs(
            root_id,
            self._reader,
            existing_inputs=existing_inputs,
            task_inputs=task_inputs,
            plan=plan,
        )

    def evaluate_execution_assumptions(
        self,
        root_id: str,
        *,
        existing_inputs: dict[str, Fact] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> AssumptionEvaluation:
        return self._engine.evaluate_execution_assumptions(
            root_id,
            self._reader,
            existing_inputs=existing_inputs,
            plan=plan,
        )

    def evaluate_assumptions(
        self,
        root_id: str,
        *,
        existing_inputs: dict[str, Fact] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> AssumptionEvaluation:
        return self._engine.evaluate_assumptions(
            root_id,
            self._reader,
            existing_inputs=existing_inputs,
            plan=plan,
        )

    def preview_plan(
        self,
        *,
        task_id: str,
        root_id: str,
        inputs: dict[str, Fact] | None = None,
        lazy: bool = False,
    ) -> ExecutionPlan:
        slug = normalize_root_id(root_id)
        return self._engine.build_plan(
            task_id=task_id,
            root_id=slug,
            inputs=inputs or {},
            reader=self._reader,
            lazy=lazy,
        )

    def pending_decision_interactions_for_root(
        self,
        root_id: str,
        *,
        existing_inputs: dict[str, Fact] | None = None,
    ) -> list:
        from engine.graph.node_interaction import (
            collect_root_interactions,
            pending_decision_interactions,
        )

        slug = normalize_root_id(root_id)
        specs = collect_root_interactions(self._reader, slug)
        return pending_decision_interactions(specs, existing_inputs or {})

    def resolve_and_propose_path_inputs(
        self,
        root_id: str,
        *,
        task_id: str,
        existing_inputs: dict[str, Fact] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> dict[str, Fact]:
        return self._engine.resolve_and_propose_path_inputs(
            root_id,
            self._reader,
            task_id=task_id,
            existing_inputs=existing_inputs,
            plan=plan,
        )

    def evaluate_expansion_interactions(
        self,
        root_id: str,
        *,
        existing_inputs: dict[str, Fact] | None = None,
        plan: ExecutionPlan | None = None,
    ) -> AssumptionEvaluation:
        return self._engine.evaluate_expansion_interactions(
            root_id,
            self._reader,
            existing_inputs=existing_inputs,
            plan=plan,
        )

    def expansion_ready_nodes(
        self,
        node_ids: list[str],
        *,
        existing_inputs: dict[str, Fact] | None = None,
    ) -> list[str]:
        return self._engine.expansion_ready_nodes(
            node_ids,
            self._reader,
            existing_inputs=existing_inputs,
        )

    def expansion_gate_ready(
        self,
        root_id: str,
        *,
        existing_inputs: dict[str, Fact] | None = None,
    ) -> bool:
        return self._engine.expansion_gate_ready(
            root_id,
            self._reader,
            existing_inputs=existing_inputs,
        )

    def seed_parameter_registry(
        self,
        root_id: str,
        *,
        existing_inputs: dict[str, Fact] | None = None,
    ):
        return self._engine.seed_parameter_registry(
            root_id,
            self._reader,
            existing_inputs=existing_inputs,
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
        from engine.state.goal_migration import goals_from_planning_summary
        from engine.state.goal_satisfaction import refresh_goal_satisfaction

        task = self._state.get_task(task_id)
        if workflow:
            self._state.store_output(task_id, "workflow", workflow)
        if selected_root:
            self._state.store_output(task_id, "selected_root", selected_root)
        self._state.set_active_nodes(task_id, active_nodes)
        task = self._state.get_task(task_id)
        task.outputs["selected_nodes"] = list(planning_summary.get("selected_nodes") or active_nodes)
        task.outputs["path_decision"] = planning_summary.get("path_decision")
        task.execution_context.goal_store = goals_from_planning_summary(
            planning_summary,
            task_id=task_id,
            workflow_id=workflow or selected_root,
        )
        refresh_goal_satisfaction(task)
        self._state.replace_task(task_id, task)
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

    def persist_proposed_inputs(
        self,
        task_id: str,
        proposed: dict[str, Fact],
    ) -> Task:
        for fact in proposed.values():
            task = self._state.get_task(task_id)
            if fact.key not in task.fact_store.active_facts():
                self._state.store_input(task_id, fact)
        return self._state.get_task(task_id)

    def persist_parameter_registry(
        self,
        task_id: str,
        registry: dict,
    ) -> Task:
        return self._state.store_parameter_registry(task_id, registry)


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
