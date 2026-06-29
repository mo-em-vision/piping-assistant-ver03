"""Adapters from existing task state to runtime workflow state."""

from __future__ import annotations

from typing import Any

from models.input import EngineeringInput
from models.task import Task
from models.workflow_state import WorkflowState

from .state_manager import StepProgress


_CONTROL_OUTPUT_KEYS = {
    "workflow",
    "selected_root",
    "graph_root",
    "graph_version",
    "planning_summary",
    "_execution_trace",
    "_validation_trace",
}


def build_workflow_state(
    task: Task,
    *,
    step_progress: list[StepProgress] | None = None,
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

    return WorkflowState(
        task_id=task.task_id,
        workflow_id=workflow_id,
        current_node=_current_node(task, progress),
        visited_nodes=visited_nodes,
        variable_values=_variable_values(task),
        lookup_results=_lookup_results(task),
        selections=_selections(task),
        warnings=tuple(task.warnings),
        errors=_errors(task),
        history=_history(progress),
    )


def _current_node(task: Task, progress: list[StepProgress]) -> str | None:
    if task.active_nodes:
        return task.active_nodes[-1]
    if progress:
        return progress[-1].step_id
    return None


def _variable_values(task: Task) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, engineering_input in task.inputs.items():
        values[key] = _input_value(engineering_input)
    for key, value in task.outputs.items():
        if key in _CONTROL_OUTPUT_KEYS or key.endswith("_lookup"):
            continue
        values[key] = value
    return values


def _input_value(engineering_input: EngineeringInput) -> dict[str, Any]:
    return {
        "value": engineering_input.value,
        "unit": engineering_input.unit,
        "source": engineering_input.source.value,
        "status": engineering_input.status.value,
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
