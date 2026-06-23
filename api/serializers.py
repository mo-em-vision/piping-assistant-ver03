"""Serialize backend models for the desktop REST API."""

from __future__ import annotations

from typing import Any

from api.error_catalog import enrich_api_error_payload
from api.output_blocks import build_display_outputs
from api.parameter_definitions import build_parameter_definitions
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from engine.state.state_manager import TaskStateManager
from models.task import Task, TaskStatus

WORKFLOW_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": PIPE_WALL_THICKNESS_DESIGN,
        "name": "Pipe Thickness Calculation",
        "description": "ASME B31.3 wall thickness design workflow",
        "discipline": "Piping",
        "available": True,
    },
    {
        "id": "flange_selection",
        "name": "Flange Selection",
        "description": "Select flanges for piping systems",
        "discipline": "Piping",
        "available": False,
    },
    {
        "id": "material_selection",
        "name": "Material Selection",
        "description": "Choose materials from standards databases",
        "discipline": "Materials",
        "available": False,
    },
    {
        "id": "tank_design",
        "name": "Tank Design",
        "description": "API 650 storage tank design workflow",
        "discipline": "Mechanical",
        "available": False,
    },
    {
        "id": "standards_lookup",
        "name": "Standards Lookup",
        "description": "Search and navigate engineering standards",
        "discipline": "Reference",
        "available": False,
    },
)

_WORKFLOW_BY_ID = {item["id"]: item for item in WORKFLOW_CATALOG}

_HIDDEN_UNITS = frozenset({"dimensionless", ""})


def workflow_catalog() -> list[dict[str, Any]]:
    return [dict(item) for item in WORKFLOW_CATALOG]


def _workflow_meta(workflow_id: str) -> dict[str, Any]:
    return _WORKFLOW_BY_ID.get(
        workflow_id,
        {
            "id": workflow_id,
            "name": workflow_id.replace("_", " ").title(),
            "description": "",
            "discipline": "Engineering",
            "available": False,
        },
    )


def _task_workflow_id(task: Task) -> str:
    workflow = task.outputs.get("workflow")
    if isinstance(workflow, str) and workflow:
        return workflow
    if task.task_id.startswith("pipe-wall-thickness"):
        return PIPE_WALL_THICKNESS_DESIGN
    return ""


def _task_display_name(task: Task) -> str:
    workflow_id = _task_workflow_id(task)
    meta = _workflow_meta(workflow_id)
    return meta["name"]


def _input_to_dict(value: Any) -> dict[str, Any]:
    return {
        "input_id": value.input_id,
        "value": value.value,
        "unit": value.unit,
        "source": value.source.value,
        "status": value.status.value,
        "default": value.default,
        "requires_confirmation": value.requires_confirmation,
        "display_value": _format_display_value(value.value, value.unit),
    }


def _format_display_value(value: Any, unit: str | None) -> str | None:
    if value is None:
        return None
    if unit and unit not in _HIDDEN_UNITS:
        return f"{value} {unit}"
    return str(value)


def _input_display(task: Task, input_id: str) -> str | None:
    engineering_input = task.inputs.get(input_id)
    if engineering_input is None:
        return None
    return _format_display_value(engineering_input.value, engineering_input.unit)


def _step(
    *,
    step_id: str,
    title: str,
    status: str,
    value: Any = None,
    unit: str | None = None,
    display_value: str | None = None,
    hint: str | None = None,
) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "status": status,
        "value": value,
        "unit": unit,
        "display_value": display_value,
        "hint": hint,
    }


def _build_pipe_wall_timeline(task: Task, planning: dict[str, Any]) -> list[dict[str, Any]]:
    missing_inputs = set(planning.get("missing_inputs") or [])
    missing_assumptions = set(planning.get("missing_assumptions") or [])

    material_done = "material" in task.inputs and "material" not in missing_inputs
    pressure_done = "design_pressure" in task.inputs and "design_pressure" not in missing_inputs
    thickness_output = task.outputs.get("required_thickness") or task.outputs.get("thickness")
    thickness_done = thickness_output is not None
    report_done = task.status == TaskStatus.COMPLETED

    timeline: list[dict[str, Any]] = []

    if material_done:
        material_status = "done"
        material_hint = None
    elif "material" in missing_inputs:
        material_status = "active"
        material_hint = "Waiting for material selection"
    else:
        material_status = "pending"
        material_hint = None

    timeline.append(
        _step(
            step_id="material",
            title="Material",
            status=material_status,
            display_value=_input_display(task, "material"),
            hint=material_hint,
        )
    )

    if pressure_done:
        pressure_status = "done"
        pressure_hint = None
    elif "design_pressure" in missing_inputs:
        pressure_status = "active" if material_done else "pending"
        pressure_hint = "Waiting for design pressure"
    else:
        pressure_status = "pending"
        pressure_hint = None

    timeline.append(
        _step(
            step_id="design_pressure",
            title="Pressure",
            status=pressure_status,
            display_value=_input_display(task, "design_pressure"),
            hint=pressure_hint,
        )
    )

    if thickness_done:
        thickness_status = "done"
        thickness_hint = None
        thickness_display = _format_display_value(thickness_output, task.outputs.get("thickness_unit"))
    elif material_done and pressure_done and not missing_assumptions:
        thickness_status = "active"
        thickness_hint = "Waiting for thickness calculation"
        thickness_display = None
    elif material_done and pressure_done:
        thickness_status = "active"
        thickness_hint = "Complete remaining assumptions before calculation"
        thickness_display = None
    else:
        thickness_status = "pending"
        thickness_hint = None
        thickness_display = None

    timeline.append(
        _step(
            step_id="thickness",
            title="Thickness",
            status=thickness_status,
            display_value=thickness_display,
            hint=thickness_hint,
        )
    )

    timeline.append(
        _step(
            step_id="report",
            title="Report",
            status="done" if report_done else "pending",
            hint=None if report_done else "Available after calculation completes",
        )
    )

    return timeline


def _build_progress_steps(task: Task, planning: dict[str, Any]) -> list[dict[str, Any]]:
    workflow_id = _task_workflow_id(task)
    if workflow_id == PIPE_WALL_THICKNESS_DESIGN:
        return _build_pipe_wall_timeline(task, planning)

    steps: list[dict[str, Any]] = []
    missing_inputs = set(planning.get("missing_inputs") or [])

    for input_id, engineering_input in task.inputs.items():
        if input_id in missing_inputs:
            status = "active"
        elif engineering_input.status.value in {"confirmed", "pending"}:
            status = "done"
        else:
            status = "pending"
        steps.append(
            _step(
                step_id=input_id,
                title=input_id.replace("_", " ").title(),
                status=status,
                value=engineering_input.value,
                unit=engineering_input.unit,
                display_value=_format_display_value(engineering_input.value, engineering_input.unit),
            )
        )

    report_status = "done" if task.status == TaskStatus.COMPLETED else "pending"
    steps.append(_step(step_id="report", title="Report", status=report_status))
    return steps


def task_summary(task: Task) -> dict[str, Any]:
    workflow_id = _task_workflow_id(task)
    meta = _workflow_meta(workflow_id)
    planning = task.outputs.get("planning_summary") or {}
    if not isinstance(planning, dict):
        planning = {}

    return {
        "id": task.task_id,
        "name": _task_display_name(task),
        "description": str(planning.get("goal") or meta["description"]),
        "discipline": meta["discipline"],
        "workflow_id": workflow_id,
        "status": task.status.value,
    }


def task_state(task: Task, manager: TaskStateManager) -> dict[str, Any]:
    workflow_id = _task_workflow_id(task)
    meta = _workflow_meta(workflow_id)
    planning = task.outputs.get("planning_summary") or {}
    if not isinstance(planning, dict):
        planning = {}

    timeline = _build_progress_steps(task, planning)
    step_progress = [
        {"step_id": step.step_id, "status": step.status, "result": step.result}
        for step in manager.list_step_progress(task.task_id)
    ]

    completed = sum(1 for step in timeline if step["status"] == "done")
    active = next((step for step in timeline if step["status"] == "active"), None)

    return {
        "task_id": task.task_id,
        "name": _task_display_name(task),
        "workflow_id": workflow_id,
        "discipline": meta["discipline"],
        "description": str(planning.get("goal") or meta["description"]),
        "status": task.status.value,
        "active_nodes": list(task.active_nodes),
        "progress": {
            "timeline": timeline,
            "steps": timeline,
            "completed_count": completed,
            "total_count": len(timeline),
            "current_step_id": active["id"] if active else None,
            "missing_inputs": list(planning.get("missing_inputs") or []),
            "missing_assumptions": list(planning.get("missing_assumptions") or []),
            "step_progress": step_progress,
        },
        "inputs": {key: _input_to_dict(value) for key, value in task.inputs.items()},
        "outputs": dict(task.outputs),
        "warnings": list(task.warnings),
        "parameters": build_parameter_definitions(task),
        "display_outputs": build_display_outputs(task),
        "options": {
            "available_workflows": [item for item in WORKFLOW_CATALOG if item["available"]],
        },
        "errors": _build_task_errors(task),
    }


def _build_task_errors(task: Task) -> list[dict[str, Any]]:
    if task.status != TaskStatus.INVALIDATED:
        return []

    message = "The engineering calculation could not complete with the current task state."
    if task.warnings:
        message = str(task.warnings[0])

    details: dict[str, Any] = {"task_id": task.task_id}
    if len(task.warnings) > 1:
        details["warnings"] = list(task.warnings)

    return [enrich_api_error_payload("calculation_failed", message, details=details)]
