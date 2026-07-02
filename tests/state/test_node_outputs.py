"""Node output builder tests (Phase 11)."""

from __future__ import annotations

from pathlib import Path

from api.json_encoding import json_safe
from engine.executor.executor import execute_workflow
from engine.reference.standards_reader import StandardsReader
from engine.state import TaskStateManager
from engine.state.node_outputs import build_node_outputs
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import sample_inputs
from tests.helpers.facts import fact_get_value, legacy_input
from engine.state.fact_migration import fact_from_engineering_input
from models.fact import SourceType, ValidationStatus


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_equation_node_output_includes_required_thickness() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "node-outputs-equation"
    manager.create_task(task_id)
    for engineering_input in sample_inputs().values():
        manager.store_input(task_id, engineering_input)

    execute_workflow(
        task_id,
        "pipe_wall_thickness_design",
        state=manager,
        reader=reader,
    )

    task = manager.get_task(task_id)
    workflow_state = manager.get_workflow_state(task_id, reader=reader)
    outputs = workflow_state.node_outputs.get("B313-eq-wall-thickness")
    assert outputs is not None
    labels = {item.label for item in outputs}
    names = {item.name for item in outputs}
    assert "Pressure design thickness" in labels or "thickness" in names or "t" in names
    assert any(item.value is not None and item.value > 0 for item in outputs)


def test_selection_output_includes_material() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "node-outputs-selection"
    manager.create_task(task_id)
    manager.store_input(
        task_id, fact_from_engineering_input(legacy_input(input_id="material",
            value="astm_a106_gr_b",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    manager.store_output(task_id, "workflow", "pipe_wall_thickness_design")
    task = manager.get_task(task_id)
    workflow_state = manager.get_workflow_state(task_id, reader=reader)

    material_outputs = workflow_state.node_outputs.get("B313-param-material")
    assert material_outputs is not None
    assert material_outputs[0].name == "material"
    assert material_outputs[0].label == "Material"
    assert material_outputs[0].value == "astm_a106_gr_b"


def test_workflow_completion_output_when_task_completed() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "node-outputs-workflow"
    manager.create_task(task_id)
    for engineering_input in sample_inputs().values():
        manager.store_input(task_id, engineering_input)

    execute_workflow(
        task_id,
        "pipe_wall_thickness_design",
        state=manager,
        reader=reader,
    )
    task = manager.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED

    workflow_state = manager.get_workflow_state(task_id, reader=reader)
    workflow_outputs = workflow_state.node_outputs.get("B313-WF-PIPE-WALL-THICKNESS")
    assert workflow_outputs is not None
    status_outputs = [item for item in workflow_outputs if item.name == "workflow_status"]
    assert status_outputs
    assert status_outputs[0].label == "Completed Task"
    assert status_outputs[0].value == "completed"


def test_workflow_state_serializes_node_outputs() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "node-outputs-serialize"
    manager.create_task(task_id)
    for engineering_input in sample_inputs().values():
        manager.store_input(task_id, engineering_input)
    execute_workflow(task_id, "pipe_wall_thickness_design", state=manager, reader=reader)

    payload = json_safe(manager.get_workflow_state(task_id, reader=reader), task_id=
        task_id, workflow_id=str(manager.get_task(
        task_id).outputs.get('workflow') or '')))
    assert payload["version"] == "6"
    assert "node_outputs" in payload
    assert "B313-eq-wall-thickness" in payload["node_outputs"]
    assert payload["node_outputs"]["B313-eq-wall-thickness"][0]["label"]
