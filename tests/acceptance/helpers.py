"""Helpers for acceptance criteria workflow tests."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from engine.executor.executor import execute_workflow
from engine.planner.planner import Planner
from engine.reports.report_data import build_report_from_task
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.agent import IntentResult
from models.execution import ExecutionResult, ExecutionStatus
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task, TaskStatus

PIPE_WALL_THICKNESS_ROOT = "pipe_wall_thickness_design"
WALL_THICKNESS_NODE = "B313-eq-wall-thickness"
EXTERNAL_WALL_THICKNESS_NODE = "B313-304.1.3"
MATERIAL_STRESS_NODE = "B313-lookup-allowable-stress"
DEFINITION_SECTION_NODE = "B313-304.1.1"


def straight_section_assumption() -> EngineeringInput:
    return EngineeringInput(
        input_id="straight_pipe_section",
        value=True,
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )


def internal_pressure_assumption() -> EngineeringInput:
    return EngineeringInput(
        input_id="pressure_loading",
        value="internal_pressure",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )


def external_pressure_assumption() -> EngineeringInput:
    return EngineeringInput(
        input_id="pressure_loading",
        value="external_pressure",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )


def confirmed_default_inputs() -> dict[str, EngineeringInput]:
    return {
        "weld_joint_efficiency": EngineeringInput(
            input_id="weld_joint_efficiency",
            value=1.0,
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "weld_strength_reduction": EngineeringInput(
            input_id="weld_strength_reduction",
            value=1.0,
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "temperature_coefficient": EngineeringInput(
            input_id="temperature_coefficient",
            value=0.4,
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }


def sample_inputs(
    *,
    pressure: float | str = 500,
    diameter: float = 10,
    material: str = "astm_a106_gr_b",
    temperature: float = 200,
) -> dict[str, EngineeringInput]:
    inputs = {
        "straight_pipe_section": straight_section_assumption(),
        "pressure_loading": internal_pressure_assumption(),
        "d_input_mode": EngineeringInput(
            input_id="d_input_mode",
            value="direct_od",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "design_pressure": EngineeringInput(
            input_id="design_pressure",
            value=pressure,
            unit="psi",
            source=InputSource.USER,
            original_value=pressure if isinstance(pressure, (int, float)) else None,
            original_unit="psi",
        ),
        "outside_diameter": EngineeringInput(
            input_id="outside_diameter",
            value=diameter,
            unit="in",
            source=InputSource.USER,
            original_value=diameter,
            original_unit="in",
        ),
        "material": EngineeringInput(
            input_id="material",
            value=material,
            unit="dimensionless",
            source=InputSource.USER,
        ),
        "design_temperature": EngineeringInput(
            input_id="design_temperature",
            value=temperature,
            unit="F",
            source=InputSource.USER,
            original_value=temperature,
            original_unit="F",
        ),
        "joint_category": EngineeringInput(
            input_id="joint_category",
            value="seamless",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "corrosion_allowance": EngineeringInput(
            input_id="corrosion_allowance",
            value=0.5,
            unit="mm",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }
    inputs.update(confirmed_default_inputs())
    return inputs


def pipe_thickness_intent() -> IntentResult:
    return IntentResult(
        intent=PIPE_WALL_THICKNESS_ROOT,
        domain="piping",
        workflow=PIPE_WALL_THICKNESS_ROOT,
        confidence=0.95,
    )


def create_task_with_inputs(
    manager: TaskStateManager,
    task_id: str,
    *,
    inputs: dict[str, EngineeringInput] | None = None,
    status: TaskStatus = TaskStatus.AWAITING_INPUT,
) -> Task:
    manager.create_task(task_id, status=status)
    for engineering_input in (inputs or sample_inputs()).values():
        manager.store_input(task_id, engineering_input)
    return manager.get_task(task_id)


def run_completed_workflow(
    manager: TaskStateManager,
    reader: StandardsReader,
    task_id: str = "pipe-wall-thickness-design-acceptance",
    *,
    inputs: dict[str, EngineeringInput] | None = None,
) -> ExecutionResult:
    if task_id not in {task.task_id for task in manager.list_tasks()}:
        create_task_with_inputs(manager, task_id, inputs=inputs)
    elif inputs:
        for engineering_input in inputs.values():
            manager.store_input(task_id, engineering_input)

    return execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=manager, reader=reader)


def plan_pipe_thickness(
    reader: StandardsReader,
    manager: TaskStateManager,
    task: Task,
    *,
    user_message: str = "Calculate pipe thickness",
) -> Any:
    return Planner(reader, state=manager).plan(
        pipe_thickness_intent(),
        task,
        user_message=user_message,
    )


def normalize_execution_trace(trace: Any) -> str:
    if not isinstance(trace, list):
        return json.dumps(trace, sort_keys=True, default=str)
    cleaned = []
    for entry in trace:
        if isinstance(entry, dict):
            cleaned.append(
                {key: value for key, value in entry.items() if key not in {"timestamp", "execution_id"}}
            )
        else:
            cleaned.append(entry)
    return json.dumps(cleaned, sort_keys=True, default=str)


def measure_graph_plan_time(reader: StandardsReader, *, iterations: int = 5) -> float:
    from engine.graph.graph_engine import GraphEngine

    engine = GraphEngine()
    start = time.perf_counter()
    for index in range(iterations):
        engine.build_plan(
            task_id=f"perf-{index}",
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs={},
            reader=reader,
        )
    return (time.perf_counter() - start) / iterations


def audit_payload(task: Task) -> dict[str, Any]:
    report = None
    return {
        "graph_version": task.outputs.get("graph_version"),
        "node_versions": _node_versions_from_trace(task),
        "inputs": {key: inp.value for key, inp in task.inputs.items()},
        "validation_events": task.outputs.get("_validation_trace"),
        "execution_trace": task.outputs.get("_execution_trace"),
        "report_data": report,
    }


def _node_versions_from_trace(task: Task) -> dict[str, str]:
    versions: dict[str, str] = {}
    trace = task.outputs.get("_execution_trace")
    if isinstance(trace, list):
        for entry in trace:
            if isinstance(entry, dict) and entry.get("node_id") and entry.get("node_version"):
                versions[str(entry["node_id"])] = str(entry["node_version"])
    return versions


def rebuild_report_from_task(task: Task, reader: StandardsReader) -> Any:
    return build_report_from_task(task, reader, user_request="Acceptance replay")
