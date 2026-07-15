"""Helpers for acceptance criteria workflow tests."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from engine.executor.executor import execute_workflow
from engine.planner.planner import Planner
from engine.reports.report_data import build_report_from_task
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_reader import StandardsReader
from engine.router import MAWP_DESIGN
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.agent import IntentResult
from models.execution import ExecutionResult, ExecutionStatus
from models.fact import fact_scalar_value
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task, TaskStatus
from tests.helpers.facts import fact_get_value

PIPE_WALL_THICKNESS_ROOT = "pipe_wall_thickness_design"
MAWP_ROOT = MAWP_DESIGN
WALL_THICKNESS_NODE = "304.1.2-a"
WALL_THICKNESS_EQUATION_NODE = "asme-b313-304-1-2-eq-3a"
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
        "weld_joint_strength_reduction_factor_W": EngineeringInput(
            input_id="weld_joint_strength_reduction_factor_W",
            value=1.0,
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "temperature_coefficient_Y": EngineeringInput(
            input_id="temperature_coefficient_Y",
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
        "outside_diameter__resolution_branch": EngineeringInput(
            input_id="outside_diameter__resolution_branch",
            value="direct_od",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "internal_design_gage_pressure": EngineeringInput(
            input_id="internal_design_gage_pressure",
            value=pressure,
            unit="psi",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
            original_value=pressure if isinstance(pressure, (int, float)) else None,
            original_unit="psi",
        ),
        "outside_diameter": EngineeringInput(
            input_id="outside_diameter",
            value=diameter,
            unit="in",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
            original_value=diameter,
            original_unit="in",
        ),
        "material_grade": EngineeringInput(
            input_id="material_grade",
            value=material,
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "design_temperature": EngineeringInput(
            input_id="design_temperature",
            value=temperature,
            unit="F",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
            original_value=temperature,
            original_unit="F",
        ),
        "pipe_construction_type": EngineeringInput(
            input_id="pipe_construction_type",
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
        "metallurgical_group": EngineeringInput(
            input_id="metallurgical_group",
            value="ferritic_steels",
            unit="dimensionless",
            source=InputSource.SYSTEM,
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
    task = manager.create_task(task_id, status=status)
    workflow_id = str(task.outputs.get("workflow") or "")
    for engineering_input in (inputs or sample_inputs()).values():
        manager.store_input(
            task_id,
            fact_from_engineering_input(
                engineering_input,
                task_id=task_id,
                workflow_id=workflow_id,
            ),
        )
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
        task = manager.get_task(task_id)
        workflow_id = str(task.outputs.get("workflow") or "")
        for engineering_input in inputs.values():
            manager.store_input(
                task_id,
                fact_from_engineering_input(
                    engineering_input,
                    task_id=task_id,
                    workflow_id=workflow_id,
                ),
            )

    return execute_workflow(task_id, PIPE_WALL_THICKNESS_ROOT, state=manager, reader=reader)


def mawp_sample_inputs() -> dict[str, EngineeringInput]:
    """Confirmed inputs sufficient to execute the MAWP workflow end-to-end."""
    inputs = {
        "straight_pipe_section": straight_section_assumption(),
        "pressure_loading": internal_pressure_assumption(),
        "outside_diameter__resolution_branch": EngineeringInput(
            input_id="outside_diameter__resolution_branch",
            value="direct_od",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "wall_thickness_basis": EngineeringInput(
            input_id="wall_thickness_basis",
            value="measured_actual",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "outside_diameter": EngineeringInput(
            input_id="outside_diameter",
            value=10.0,
            unit="in",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
            original_value=10.0,
            original_unit="in",
        ),
        "actual_wall_thickness": EngineeringInput(
            input_id="actual_wall_thickness",
            value=6.35,
            unit="mm",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
            original_value=6.35,
            original_unit="mm",
        ),
        "corrosion_allowance": EngineeringInput(
            input_id="corrosion_allowance",
            value=0.5,
            unit="mm",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "material_grade": EngineeringInput(
            input_id="material_grade",
            value="astm_a106_gr_b",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "design_temperature": EngineeringInput(
            input_id="design_temperature",
            value=200.0,
            unit="F",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
            original_value=200.0,
            original_unit="F",
        ),
        "pipe_construction_type": EngineeringInput(
            input_id="pipe_construction_type",
            value="seamless",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "metallurgical_group": EngineeringInput(
            input_id="metallurgical_group",
            value="ferritic_steels",
            unit="dimensionless",
            source=InputSource.SYSTEM,
            status=InputStatus.CONFIRMED,
        ),
    }
    inputs.update(confirmed_default_inputs())
    return inputs


def create_workflow_task_with_inputs(
    manager: TaskStateManager,
    task_id: str,
    workflow_id: str,
    *,
    inputs: dict[str, EngineeringInput],
    status: TaskStatus = TaskStatus.AWAITING_INPUT,
) -> Task:
    task = manager.create_task(task_id, status=status)
    task.outputs["workflow"] = workflow_id
    task.outputs["selected_root"] = workflow_id
    for engineering_input in inputs.values():
        manager.store_input(
            task_id,
            fact_from_engineering_input(
                engineering_input,
                task_id=task_id,
                workflow_id=workflow_id,
            ),
        )
    return manager.get_task(task_id)


def run_completed_mawp_workflow(
    manager: TaskStateManager,
    reader: StandardsReader,
    task_id: str = "mawp-design-acceptance",
    *,
    inputs: dict[str, EngineeringInput] | None = None,
) -> ExecutionResult:
    task_ids = {task.task_id for task in manager.list_tasks()}
    if task_id not in task_ids:
        create_workflow_task_with_inputs(
            manager,
            task_id,
            MAWP_ROOT,
            inputs=inputs or mawp_sample_inputs(),
        )
    elif inputs:
        task = manager.get_task(task_id)
        for engineering_input in inputs.values():
            manager.store_input(
                task_id,
                fact_from_engineering_input(
                    engineering_input,
                    task_id=task_id,
                    workflow_id=MAWP_ROOT,
                ),
            )

    return execute_workflow(task_id, MAWP_ROOT, state=manager, reader=reader)


def load_workflow_frontmatter(workflow_stem: str) -> dict:
    path = Path(__file__).resolve().parents[2] / "workflows" / f"{workflow_stem}.yaml"
    meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
    return meta


def refresh_completed_workflow_planning(
    task: Task,
    reader: StandardsReader,
) -> None:
    from api.workflow_bootstrap import refresh_task_planning
    from engine.planner.workflow_goal_metadata import resolve_root_goal_spec
    from engine.state.goal_satisfaction import refresh_goal_satisfaction
    from engine.state.task_facts import store_fact
    from models.fact import FactClass, FactProvenance, FactSource, SourceType, ValidationStatus, build_numeric_fact

    refresh_task_planning(task, reader, propose_defaults=False)
    spec = resolve_root_goal_spec(reader, str(task.outputs.get("workflow") or ""))
    output_value = task.outputs.get(spec.target_field)
    if output_value is None and spec.target_field == "minimum_required_thickness":
        output_value = task.outputs.get("t_m")
    unit = str(task.outputs.get(f"{spec.target_field}_unit") or "").strip()
    if not unit:
        if spec.target_field == "mawp":
            unit = "psi"
        elif spec.target_field == "minimum_required_thickness":
            unit = "mm"
    if output_value is not None and task.fact_store.active_fact(spec.target_field) is None:
        store_fact(
            task,
            build_numeric_fact(
                key=spec.target_field,
                parameter=spec.target_field,
                amount=float(output_value),
                unit=str(task.outputs.get(f"{spec.target_field}_unit") or unit),
                fact_class=FactClass.CALCULATED,
                source=FactSource(
                    source_type=SourceType.EQUATION,
                    source_id="workflow-completion-test",
                ),
                provenance=FactProvenance(task_id=task.task_id),
                validation_status=ValidationStatus.VALIDATED,
            ),
        )
    refresh_goal_satisfaction(task)


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
        "inputs": {
            key: fact_scalar_value(fact)
            for key, fact in task.fact_store.active_facts().items()
        },
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
