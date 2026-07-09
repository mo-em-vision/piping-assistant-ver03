"""Execution Layer — deterministic workflow runtime."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from engine.events.event_logger import EventLogger
from engine.execution.lifecycle_emitter import WorkflowLifecycleEmitter, is_executable_node
from engine.executor.node_runner import NodeRunner
from engine.graph.graph_engine import GraphEngine
from engine.graph.definition_equations import (
    pending_definition_equation_inputs,
    try_complete_definition_equations,
)
from engine.inspection.dev_guard import inspection_enabled
from engine.inspection.operation_tracker import track_operation
from engine.inspection.performance_trace import add_summary_span, perf_span
from engine.inspection.models import GraphEdgeRef
from engine.inspection.trace import enrich_execution_result_trace, persist_plan_metadata
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
        with perf_span("execute_plan", "execution", notes=f"nodes={len(plan.execution_order)}"):
            return self._execute_plan_impl(plan, state=state)

    def _execute_plan_impl(
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
        store = self._reader.graph_store
        lifecycle = WorkflowLifecycleEmitter(store) if store.available else None

        def persist_lifecycle() -> list[dict[str, Any]]:
            if lifecycle is None:
                return []
            payload = lifecycle.to_dicts()
            state.store_output(plan.task_id, "_lifecycle_events", payload)
            return payload

        with perf_span("validate_plan", "validation", notes=f"nodes={len(plan.execution_order)}"):
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
                lifecycle_events=persist_lifecycle(),
            )

        if plan_validation.status == ComplianceStatus.INCOMPLETE:
            state.store_output(plan.task_id, "_validation_trace", validation_trace)
            state.update_task_status(plan.task_id, TaskStatus.AWAITING_INPUT)
            return ExecutionResult(
                plan=plan,
                node_results=node_results,
                status=ExecutionStatus.AWAITING_INPUT,
                events=self._events.to_dicts(),
                lifecycle_events=persist_lifecycle(),
            )

        for warning in plan_validation.warnings:
            state.add_warning(plan.task_id, warning.message)

        task = state.get_task(plan.task_id)
        if not task.outputs.get("workflow"):
            state.store_output(plan.task_id, "workflow", plan.root)
        state.store_output(plan.task_id, "graph_root", plan.root)
        if plan.graph_version:
            graph_payload: dict[str, Any] = {
                "graph_id": plan.graph_version.graph_id,
                "nodes": list(plan.graph_version.nodes),
            }
            if inspection_enabled():
                graph_payload["edges"] = [
                    {
                        "from_node": edge.from_node,
                        "to_node": edge.to_node,
                        "type": edge.type.value if hasattr(edge.type, "value") else str(edge.type),
                    }
                    for edge in plan.graph_version.edges
                ]
            state.store_output(
                plan.task_id,
                "graph_version",
                graph_payload,
            )

        if inspection_enabled():
            task = state.get_task(plan.task_id)
            outputs = dict(task.outputs)
            persist_plan_metadata(outputs, plan)
            for key, value in outputs.items():
                if key.startswith("_"):
                    state.store_output(plan.task_id, key, value)

        plan_edges = _plan_edge_refs(plan)
        step_index = 0
        step_durations: dict[str, float] = {}

        for node_id in plan.execution_order:
            if inspection_enabled() and _should_pause(state, plan.task_id):
                overall_status = ExecutionStatus.AWAITING_INPUT
                state.update_task_status(plan.task_id, TaskStatus.AWAITING_INPUT)
                break

            record = self._reader.load(node_id)
            node_type = record.metadata.get("type")
            if node_type in {"root", "definition"}:
                continue
            if node_type == "validation_rule":
                prior_completed.add(node_id)
                continue
            if node_type == "equation" and str(record.metadata.get("execution_phase", "")) == "definition":
                prior_completed.add(node_id)
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
                persist_lifecycle()
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
                persist_lifecycle()
                break

            for warning in node_validation.warnings:
                state.add_warning(plan.task_id, warning.message)

            if lifecycle is not None:
                task = state.get_task(plan.task_id)
                context = WorkflowLifecycleEmitter.build_context(task, inputs=plan.inputs)
                lifecycle.emit_before_enter(node_id, context=context)
                lifecycle.emit_on_enter(node_id, context=context)
                if is_executable_node(record.metadata, str(node_type or "")):
                    lifecycle.emit_on_execute(node_id, context=context)

            self._events.log(EventType.CALCULATION_STARTED, node=node_id)

            started = time.perf_counter()
            result = self._runner.run(
                node_id,
                task_inputs=plan.inputs,
                dependency_outputs=dependency_outputs,
            )
            duration_ms = (time.perf_counter() - started) * 1000.0
            step_durations[node_id] = duration_ms
            node_results.append(result)

            if inspection_enabled():
                incoming, outgoing = _edges_for_node(node_id, plan_edges)
                result_payload = enrich_execution_result_trace(
                    asdict(result),
                    step_index=step_index,
                    workflow_id=plan.root,
                    node_type=str(node_type or ""),
                    duration_ms=duration_ms,
                    incoming_edge=incoming,
                    outgoing_edge=outgoing,
                    selection_reason=_selection_reason(plan, node_id),
                )
                state.store_step_progress(
                    plan.task_id,
                    node_id,
                    result.status.value,
                    result=result_payload,
                )
                step_index += 1
            else:
                state.store_step_progress(
                    plan.task_id,
                    node_id,
                    result.status.value,
                    result=asdict(result),
                )

            if result.status == NodeExecutionStatus.AWAITING_INPUT:
                overall_status = ExecutionStatus.AWAITING_INPUT
                state.update_task_status(plan.task_id, TaskStatus.AWAITING_INPUT)
                self._events.log(
                    EventType.INPUT_REQUESTED,
                    node=node_id,
                    result=result.errors,
                    payload={"missing": result.trace.get("missing_inputs", [])},
                )
                persist_lifecycle()
                break

            if result.status == NodeExecutionStatus.ERROR:
                overall_status = ExecutionStatus.ERROR
                state.update_task_status(plan.task_id, TaskStatus.INVALIDATED)
                for error_message in result.errors:
                    state.add_warning(plan.task_id, error_message)
                self._events.log(
                    EventType.WARNING_CREATED,
                    node=node_id,
                    result=result.errors,
                )
                if lifecycle is not None:
                    task = state.get_task(plan.task_id)
                    context = WorkflowLifecycleEmitter.build_context(task, inputs=plan.inputs)
                    lifecycle.emit_on_error(
                        node_id,
                        "; ".join(result.errors),
                        context=context,
                    )
                persist_lifecycle()
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
                if lifecycle is not None:
                    task = state.get_task(plan.task_id)
                    context = WorkflowLifecycleEmitter.build_context(task, inputs=plan.inputs)
                    lifecycle.emit_on_exit(node_id, context=context)
            elif result.status == NodeExecutionStatus.SKIPPED:
                prior_completed.add(node_id)

        _record_node_execution_aggregates(self._reader, step_durations)

        trace_payload = []
        for item in node_results:
            payload = asdict(item)
            if inspection_enabled():
                incoming, outgoing = _edges_for_node(item.node_id, plan_edges)
                payload = enrich_execution_result_trace(
                    payload,
                    step_index=trace_payload.__len__(),
                    workflow_id=plan.root,
                    node_type=_node_type_for(self._reader, item.node_id),
                    duration_ms=step_durations.get(item.node_id, 0.0),
                    incoming_edge=incoming,
                    outgoing_edge=outgoing,
                    selection_reason=_selection_reason(plan, item.node_id),
                )
            trace_payload.append(payload)

        if overall_status == ExecutionStatus.COMPLETED:
            task = state.get_task(plan.task_id)
            from engine.executor.pipe_schedule_recommendation import (
                append_schedule_lookup_trace_to_payload,
            )

            append_schedule_lookup_trace_to_payload(
                task,
                trace_payload,
                self._reader.standards_root,
            )

        state.store_output(plan.task_id, "_execution_trace", trace_payload)
        state.store_output(plan.task_id, "_validation_trace", validation_trace)

        lifecycle_payload = persist_lifecycle()

        if overall_status == ExecutionStatus.COMPLETED:
            task = state.get_task(plan.task_id)
            try_complete_definition_equations(task, self._reader, plan.execution_order)
            for key, value in task.outputs.items():
                state.store_output(plan.task_id, key, value)
            state.update_task_status(plan.task_id, task.status)
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

        if inspection_enabled():
            state.store_output(plan.task_id, "_execution_events", self._events.to_dicts())
            from api.inspection import persist_replay_snapshot

            task = state.get_task(plan.task_id)
            persist_replay_snapshot(task, state, self._reader)

        return ExecutionResult(
            plan=plan,
            node_results=node_results,
            status=overall_status,
            events=self._events.to_dicts(),
            lifecycle_events=lifecycle_payload,
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
    with track_operation(
        "execute_workflow",
        category="execution",
        task_id=task_id,
        root_id=root_id,
    ):
        with perf_span("execute_workflow", "execution", notes=f"root_id={root_id}"):
            task = state.get_task(task_id)
            plan = GraphEngine().build_plan(
                task_id=task_id,
                root_id=root_id,
                inputs=dict(task.fact_store.active_facts()),
                reader=reader,
            )
            executor = Executor(reader, events=events)
            return executor.execute_plan(plan, state=state)


def _plan_edge_refs(plan: ExecutionPlan) -> list[GraphEdgeRef]:
    edges: list[GraphEdgeRef] = []
    source = list(plan.dependencies)
    if plan.graph_version and plan.graph_version.edges:
        source = list(plan.graph_version.edges)
    for edge in source:
        edge_type = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
        edges.append(
            GraphEdgeRef(
                from_node=edge.from_node,
                to_node=edge.to_node,
                edge_type=edge_type,
            )
        )
    return edges


def _record_node_execution_aggregates(
    reader: StandardsReader,
    step_durations: dict[str, float],
) -> None:
    equation_count = 0
    equation_ms = 0.0
    lookup_count = 0
    lookup_ms = 0.0
    for node_id, duration_ms in step_durations.items():
        node_type = _node_type_for(reader, node_id)
        if node_type == "equation":
            equation_count += 1
            equation_ms += duration_ms
        elif node_type == "lookup":
            lookup_count += 1
            lookup_ms += duration_ms
    if equation_count:
        add_summary_span(
            "equation_evaluations",
            "equation",
            equation_ms,
            notes=f"count={equation_count}",
        )
    if lookup_count:
        add_summary_span(
            "lookup_resolutions",
            "lookup",
            lookup_ms,
            notes=f"count={lookup_count}",
        )


def _edges_for_node(
    node_id: str,
    edges: list[GraphEdgeRef],
) -> tuple[GraphEdgeRef | None, GraphEdgeRef | None]:
    incoming = next((edge for edge in edges if edge.to_node == node_id), None)
    outgoing = next((edge for edge in edges if edge.from_node == node_id), None)
    return incoming, outgoing


def _selection_reason(plan: ExecutionPlan, node_id: str) -> str:
    for item in plan.skipped_nodes:
        if str(item.get("node_id")) == node_id:
            return str(item.get("reason", "skipped"))
    return "dependency_satisfied"


def _node_type_for(reader: StandardsReader, node_id: str) -> str:
    try:
        return str(reader.load(node_id).metadata.get("type", ""))
    except FileNotFoundError:
        return ""


def _should_pause(state: TaskStateManager, task_id: str) -> bool:
    task = state.get_task(task_id)
    bp = task.outputs.get("_inspection_breakpoint")
    if not isinstance(bp, dict):
        return False
    if bp.get("step_once"):
        state.store_output(
            task_id,
            "_inspection_breakpoint",
            {**bp, "step_once": False, "paused": True},
        )
        return False
    return bool(bp.get("paused"))
