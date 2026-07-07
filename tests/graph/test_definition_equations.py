"""Tests for post-calculation definition equation planning."""

from __future__ import annotations

import pytest

from engine.graph.definition_equations import (
    pending_definition_equation_inputs,
    try_complete_definition_equations,
)
from engine.graph.graph_engine import GraphEngine
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import run_completed_workflow, sample_inputs


@pytest.fixture
def standards_reader(project_root):
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _full_inputs_without_corrosion() -> dict[str, EngineeringInput]:
    inputs = sample_inputs()
    del inputs["corrosion_allowance"]
    inputs["metallurgical_group"] = EngineeringInput(
        input_id="metallurgical_group",
        value="carbon_steel",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    inputs["material_grade"] = EngineeringInput(
        input_id="material_grade",
        value="SA-106B",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    inputs["pipe_construction_type"] = EngineeringInput(
        input_id="pipe_construction_type",
        value="seamless",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    return inputs


def _execution_order(reader: StandardsReader, task) -> tuple[str, ...]:
    plan = GraphEngine().build_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.fact_store.active_facts()),
        reader=reader,
    )
    return plan.execution_order


def test_pending_definition_inputs_after_thickness_without_corrosion(standards_reader) -> None:
    manager = TaskStateManager()
    task_id = "def-eq-pending-01"
    run_completed_workflow(manager, standards_reader, task_id, inputs=_full_inputs_without_corrosion())
    task = manager.get_task(task_id)

    assert task.outputs.get("t") is not None or task.outputs.get("required_thickness") is not None
    assert task.outputs.get("minimum_required_thickness") is None
    assert task.status == TaskStatus.AWAITING_INPUT

    pending = pending_definition_equation_inputs(
        task,
        standards_reader,
        _execution_order(standards_reader, task),
    )
    assert pending == ["corrosion_allowance"]


def test_complete_definition_equation_after_corrosion_input(standards_reader) -> None:
    manager = TaskStateManager()
    task_id = "def-eq-complete-01"
    run_completed_workflow(manager, standards_reader, task_id, inputs=_full_inputs_without_corrosion())
    task = manager.get_task(task_id)
    execution_order = _execution_order(standards_reader, task)

    manager.store_fact(
        task_id,
        fact_from_engineering_input(
            EngineeringInput(
                input_id="corrosion_allowance",
                value=0.5,
                unit="mm",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id=task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = manager.get_task(task_id)

    assert try_complete_definition_equations(task, standards_reader, execution_order) is True
    assert task.outputs.get("minimum_required_thickness") is not None
    assert task.outputs.get("t_m") is not None
    thickness_t = task.outputs.get("t") or task.outputs.get("required_thickness")
    assert thickness_t is not None
    assert task.outputs["minimum_required_thickness"] > thickness_t
    assert task.status == TaskStatus.COMPLETED
