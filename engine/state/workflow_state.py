"""Adapters from existing task state to runtime workflow state."""

from __future__ import annotations

from typing import Any

from engine.execution.lifecycle_emitter import parse_lifecycle_events
from engine.graph.documentation_resolver import resolve_workflow_documentation
from engine.presentation.presentation_engine import build_presentation
from engine.reference.standards_reader import StandardsReader
from engine.state.node_outputs import build_node_outputs
from models.fact import Fact, fact_scalar_value, fact_unit
from models.node_output import NodeOutput
from models.task import Task
from models.workflow_state import WorkflowState

from .state_manager import StepProgress
from .workflow_parameters import build_workflow_parameters

_CONTROL_OUTPUT_KEYS = {
    "workflow",
    "selected_root",
    "graph_root",
    "graph_version",
    "_execution_trace",
    "_validation_trace",
    "_lifecycle_events",
}


def build_workflow_state(
    task: Task,
    *,
    step_progress: list[StepProgress] | None = None,
    reader: StandardsReader | None = None,
) -> WorkflowState:
    """Build a serializable runtime-state view from the existing task model."""

    progress = step_progress or []
    visited_nodes = tuple(item.step_id for item in progress)
    workflow_id = str(
        task.outputs.get("workflow")
        or task.outputs.get("selected_root")
        or task.outputs.get("graph_root")
        or ""
    )
    active_nodes = set(task.active_nodes) | set(visited_nodes)
    parameters = (
        build_workflow_parameters(task, reader=reader, active_nodes=active_nodes)
        if reader is not None
        else {}
    )
    current_node = _current_node(task, progress)
    doc_node_ids = set(visited_nodes)
    if current_node:
        doc_node_ids.add(current_node)
    node_documentation = (
        resolve_workflow_documentation(
            reader,
            task,
            node_ids=doc_node_ids,
            parameters=parameters,
        )
        if reader is not None
        else {}
    )
    current_documentation = (
        node_documentation.get(current_node) if current_node else None
    )
    execution_events = parse_lifecycle_events(task.outputs.get("_lifecycle_events"))

    version = "1"
    if parameters:
        version = "2"
    if node_documentation:
        version = "3"
    if execution_events:
        version = "4"

    base_state = WorkflowState(
        task_id=task.task_id,
        workflow_id=workflow_id,
        current_node=current_node,
        visited_nodes=visited_nodes,
        variable_values=_variable_values(task),
        lookup_results=_lookup_results(task),
        selections=_selections(task),
        parameters=parameters,
        current_documentation=current_documentation,
        node_documentation=node_documentation,
        execution_events=execution_events,
        warnings=tuple(task.warnings),
        errors=_errors(task),
        history=_history(progress),
        version=version,
    )

    presentation_blocks: tuple[dict[str, Any], ...] = ()
    node_outputs: dict[str, tuple[NodeOutput, ...]] = ()
    if reader is not None:
        presentation_blocks = build_presentation(base_state, reader.graph_store)
        node_outputs = build_node_outputs(
            task,
            reader=reader,
            history=base_state.history,
        )
    if presentation_blocks:
        version = "5"
    if node_outputs:
        version = "6"

    return WorkflowState(
        task_id=base_state.task_id,
        workflow_id=base_state.workflow_id,
        current_node=base_state.current_node,
        visited_nodes=base_state.visited_nodes,
        variable_values=base_state.variable_values,
        lookup_results=base_state.lookup_results,
        selections=base_state.selections,
        parameters=base_state.parameters,
        current_documentation=base_state.current_documentation,
        node_documentation=base_state.node_documentation,
        execution_events=base_state.execution_events,
        presentation_blocks=presentation_blocks,
        node_outputs=node_outputs,
        warnings=base_state.warnings,
        errors=base_state.errors,
        history=base_state.history,
        version=version,
    )


def _current_node(task: Task, progress: list[StepProgress]) -> str | None:
    if task.active_nodes:
        return task.active_nodes[-1]
    if progress:
        return progress[-1].step_id
    return None


def _variable_values(task: Task) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, engineering_input in task.fact_store.active_facts().items():
        values[key] = _input_value(engineering_input)
    for key, value in task.outputs.items():
        if key in _CONTROL_OUTPUT_KEYS or key.endswith("_lookup"):
            continue
        values[key] = value
    return values


def _input_value(fact: Fact) -> dict[str, Any]:
    return {
        "value": fact_scalar_value(fact),
        "unit": fact_unit(fact),
        "source": fact.source.source_type.value,
        "status": fact.validation.status.value,
    }


def _lookup_results(task: Task) -> dict[str, Any]:
    return {
        key: value
        for key, value in task.outputs.items()
        if key.endswith("_lookup") or key.endswith("_lookup_result")
    }


def _selections(task: Task) -> dict[str, Any]:
    return {
        key: value
        for key, value in task.outputs.items()
        if key.startswith("selected_") and key != "selected_root"
    }


def _errors(task: Task) -> tuple[str, ...]:
    errors = task.outputs.get("task_state_errors")
    if not isinstance(errors, list):
        return ()
    return tuple(str(item) for item in errors)


def _history(progress: list[StepProgress]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "node_id": item.step_id,
            "status": item.status,
            "result": item.result,
        }
        for item in progress
    )
