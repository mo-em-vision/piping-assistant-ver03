"""Tests for post-calculation definition equation planning."""

from __future__ import annotations

import pytest

from engine.graph.definition_equations import (
    pending_definition_equation_inputs,
    try_complete_definition_equations,
)
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import (
    DEFINITION_SECTION_NODE,
    MATERIAL_STRESS_NODE,
    PIPE_WALL_THICKNESS_ROOT,
    WALL_THICKNESS_NODE,
    run_completed_workflow,
    sample_inputs,
)


@pytest.fixture
def standards_reader(project_root):
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_pending_definition_inputs_after_thickness_without_corrosion(standards_reader) -> None:
    manager = TaskStateManager()
    task_id = "def-eq-pending-01"
    inputs = sample_inputs()
    del inputs["corrosion_allowance"]
    run_completed_workflow(manager, standards_reader, task_id, inputs=inputs)
    task = manager.get_task(task_id)

    assert task.outputs.get("t") is not None
    assert task.outputs.get("minimum_required_thickness") is None

    pending = pending_definition_equation_inputs(
        task,
        standards_reader,
        (
            DEFINITION_SECTION_NODE,
            MATERIAL_STRESS_NODE,
            WALL_THICKNESS_NODE,
            "B313-eq-2",
        ),
    )
    assert pending == ["corrosion_allowance"]


def test_complete_definition_equation_after_corrosion_input(standards_reader) -> None:
    manager = TaskStateManager()
    task_id = "def-eq-complete-01"
    inputs = sample_inputs()
    del inputs["corrosion_allowance"]
    run_completed_workflow(manager, standards_reader, task_id, inputs=inputs)
    task = manager.get_task(task_id)
    execution_order = (
        DEFINITION_SECTION_NODE,
        MATERIAL_STRESS_NODE,
        WALL_THICKNESS_NODE,
        "B313-eq-2",
    )

    task.inputs["corrosion_allowance"] = EngineeringInput(
        input_id="corrosion_allowance",
        value=0.5,
        unit="mm",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )

    assert try_complete_definition_equations(task, standards_reader, execution_order) is True
    assert task.outputs.get("minimum_required_thickness") is not None
    assert task.outputs.get("t_m") is not None
    assert task.outputs["minimum_required_thickness"] > task.outputs["t"]
    assert task.status == TaskStatus.COMPLETED
