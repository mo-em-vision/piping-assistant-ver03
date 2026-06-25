"""Execution Layer — deterministic workflow runtime."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from engine.events.event_logger import EventLogger
from engine.executor.node_runner import NodeRunner
from engine.graph.graph_engine import GraphEngine
from engine.graph.definition_equations import (
    pending_definition_equation_inputs,
)
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from engine.validation.validation_engine import ValidationEngine
from models.event import EventType
from models.validation import ComplianceStatus
from models.execution import (
    ExecutionPlan,
    ExecutionResult,
    ExecutionStatus,
    NodeExecutionResult,
    NodeExecutionStatus,
)
from models.task import TaskStatus


class Executor:
    """Execute an ExecutionPlan and persist results to task state."""

    def __init__(
        self,
        reader: StandardsReader,
        *,
        events: EventLogger | None = None,
        validation: ValidationEngine | None = None,
    ) -> None:
        self._reader = reader
        self._runner = NodeRunner(reader)
        self._events = events or EventLogger()
        self._validation = validation or ValidationEngine(reader, events=self._events)

    @property
    def event_logger(self) -> EventLogger:
        return self._events

    def execute_plan(
        self,
        plan: ExecutionPlan,
        *,
        state: TaskStateManager,
    ) -> ExecutionResult:
        task = state.get_task(plan.task_id)
        node_results: list[NodeExecutionResult] = []
        dependency_outputs: dict[str, Any] = {}
        prior_completed: set[str] = set()
        validation_trace: list[dict[str, Any]] = []
        overall_status = ExecutionStatus.COMPLETED

        plan_validation = self._validation.validate_plan(plan, task)
        validation_trace.append(
            {"scope": "plan", **self._validation.to_trace_entry(plan_validation)}
        )
        if plan_validation.status == ComplianceStatus.FAIL:
            state.store_output(plan.task_id, "_validation_trace", validation_trace)
            state.update_task_status(plan.task_id, TaskStatus.INVALIDATED)
            for finding in plan_validation.errors:
                state.add_warning(plan.task_id, finding.message)
            return ExecutionResult(
                plan=plan,
                node_results=node_results,
                status=ExecutionStatus.ERROR,
                events=self._events.to_dicts(),
            )

        if plan_validation.status == ComplianceStatus.INCOMPLETE:
            state.store_output(plan.task_id, "_validation_trace", validation_trace)
            state.update_task_status(plan.task_id, TaskStatus.AWAITING_INPUT)
            return ExecutionResult(
                plan=plan,
                node_results=node_results,
                status=ExecutionStatus.AWAITING_INPUT,
                events=self._events.to_dicts(),
            )

        for warning in plan_validation.warnings:
            state.add_warning(plan.task_id, warning.message)

        task = state.get_task(plan.task_id)
        if not task.outputs.get("workflow"):
            state.store_output(plan.task_id, "workflow", plan.root)
        state.store_output(plan.task_id, "graph_root", plan.root)
        if plan.graph_version:
            state.store_output(
                plan.task_id,
                "graph_version",
                {
                    "graph_id": plan.graph_version.graph_id,
                    "nodes": list(plan.graph_version.nodes),
                },
            )

        for node_id in plan.execution_order:
            node_type = self._reader.load(node_id).metadata.get("type")
            if node_type in {"root", "definition"}:
                continue

            node_validation = self._validation.validate_node(
                node_id,
                task_inputs=plan.inputs,
                dependency_outputs=dependency_outputs,
                prior_nodes_completed=prior_completed,
                overrides=self._validation.override_rules_for(task),
            )
            validation_trace.append(
                {"scope": node_id, **self._validation.to_trace_entry(node_validation)}
            )

            if node_validation.status == ComplianceStatus.FAIL:
                overall_status = ExecutionStatus.ERROR
                state.update_task_status(plan.task_id, TaskStatus.INVALIDATED)
                for finding in node_validation.errors:
                    state.add_warning(plan.task_id, finding.message)
                state.store_output(plan.task_id, "_validation_trace", validation_trace)
                break

            if node_validation.status == ComplianceStatus.INCOMPLETE:
                overall_status = ExecutionStatus.AWAITING_INPUT
                state.update_task_status(plan.task_id, TaskStatus.AWAITING_INPUT)
                self._events.log(
                    EventType.INPUT_REQUESTED,
                    node=node_id,
                    result=[finding.message for finding in node_validation.errors],
                    payload={"missing": [finding.input_id for finding in node_validation.errors if finding.input_id]},
                )
                state.store_output(plan.task_id, "_validation_trace", validation_trace)
                break

            for warning in node_validation.warnings:
                state.add_warning(plan.task_id, warning.message)

            self._events.log(EventType.CALCULATION_STARTED, node=node_id)

            result = self._runner.run(
                node_id,
                task_inputs=plan.inputs,
                dependency_outputs=dependency_outputs,
            )
            node_results.append(result)

            if result.status == NodeExecutionStatus.AWAITING_INPUT:
                overall_status = ExecutionStatus.AWAITING_INPUT
                state.update_task_status(plan.task_id, TaskStatus.AWAITING_INPUT)
                self._events.log(
                    EventType.INPUT_REQUESTED,
                    node=node_id,
                    result=result.errors,
                    payload={"missing": result.trace.get("missing_inputs", [])},
                )
                break

            if result.status == NodeExecutionStatus.ERROR:
                overall_status = ExecutionStatus.ERROR
                state.update_task_status(plan.task_id, TaskStatus.INVALIDATED)
                self._events.log(
                    EventType.WARNING_CREATED,
                    node=node_id,
                    result=result.errors,
                )
                break

            if result.status == NodeExecutionStatus.COMPLETED:
                dependency_outputs.update(result.outputs)
                prior_completed.add(node_id)
                for key, value in result.outputs.items():
                    state.store_output(plan.task_id, key, value)
                for warning in result.warnings:
                    state.add_warning(plan.task_id, warning)
                self._events.log(
                    EventType.CALCULATION_COMPLETED,
                    node=node_id,
                    result=result.outputs,
                )
            elif result.status == NodeExecutionStatus.SKIPPED:
                prior_completed.add(node_id)

            state.store_step_progress(
                plan.task_id,
                node_id,
                result.status.value,
                result=asdict(result),
            )

        trace_payload = [asdict(item) for item in node_results]
        state.store_output(plan.task_id, "_execution_trace", trace_payload)
        state.store_output(plan.task_id, "_validation_trace", validation_trace)

        if overall_status == ExecutionStatus.COMPLETED:
            task = state.get_task(plan.task_id)
            pending_definition = pending_definition_equation_inputs(
                task,
                self._reader,
                plan.execution_order,
            )
            if pending_definition:
                overall_status = ExecutionStatus.AWAITING_INPUT
                state.update_task_status(plan.task_id, TaskStatus.AWAITING_INPUT)
            else:
                state.update_task_status(plan.task_id, TaskStatus.COMPLETED)
        elif overall_status == ExecutionStatus.AWAITING_INPUT:
            state.update_task_status(plan.task_id, TaskStatus.AWAITING_INPUT)

        return ExecutionResult(
            plan=plan,
            node_results=node_results,
            status=overall_status,
            events=self._events.to_dicts(),
        )


def execute_workflow(
    task_id: str,
    root_id: str,
    *,
    state: TaskStateManager,
    reader: StandardsReader,
    events: EventLogger | None = None,
) -> ExecutionResult:
    """Build an execution plan and run it."""
    task = state.get_task(task_id)
    plan = GraphEngine().build_plan(
        task_id=task_id,
        root_id=root_id,
        inputs=dict(task.inputs),
        reader=reader,
    )
    executor = Executor(reader, events=events)
    return executor.execute_plan(plan, state=state)
