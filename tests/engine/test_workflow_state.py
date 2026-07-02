"""Runtime workflow state boundary tests."""

from __future__ import annotations

import json
from pathlib import Path

from api.json_encoding import json_safe
from engine.executor.executor import execute_workflow
from engine.reference.standards_reader import StandardsReader
from engine.state import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from tests.acceptance.helpers import sample_inputs
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_workflow_state_is_serializable_runtime_data() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "workflow-state-boundary"
    manager.create_task(task_id)
    manager.store_input(
        task_id,
        EngineeringInput(
            input_id="design_pressure",
            value=500,
            unit="psi",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    manager.store_output(task_id, "workflow", "pipe_wall_thickness_design")
    manager.store_output(task_id, "required_thickness", 0.084)
    manager.store_output(
        task_id,
        "allowable_stress_lookup",
        {"table": "A-1", "value": 193_000_000.0, "unit": "Pa"},
    )
    manager.store_output(task_id, "graph_version", {"nodes": ["B313-304.1.2"]})
    manager.add_warning(task_id, "Review corrosion allowance.")
    manager.store_step_progress(task_id, "B313-table-A-1", "completed")
    manager.store_step_progress(task_id, "B313-304.1.2", "completed")

    workflow_state = manager.get_workflow_state(task_id, reader=reader)
    payload = json_safe(workflow_state)

    json.dumps(payload)
    assert payload["task_id"] == task_id
    assert payload["workflow_id"] == "pipe_wall_thickness_design"
    assert payload["current_node"] == "B313-304.1.2"
    assert payload["visited_nodes"] == ["B313-table-A-1", "B313-304.1.2"]
    assert payload["variable_values"]["design_pressure"]["value"] == 500
    assert payload["variable_values"]["required_thickness"] == 0.084
    assert payload["lookup_results"]["allowable_stress_lookup"]["value"] == 193_000_000.0
    assert "graph_version" not in payload["variable_values"]
    assert payload["warnings"] == ["Review corrosion allowance."]
    assert payload["version"] == "6"
    assert payload["presentation_blocks"]
    assert payload["node_outputs"]
    assert any(block["type"] == "warning" for block in payload["presentation_blocks"])
    assert payload["parameters"]["design_pressure"]["dimension"] == "pressure"
    assert payload["parameters"]["design_pressure"]["source"] == "user_input"
    pressure = payload["parameters"]["design_pressure"]
    assert pressure["canonical_unit"] == "UNIT-Pa"
    assert "UNIT-psi" in pressure["allowed_units"]
    assert pressure["unit_id"] == "UNIT-psi"


def test_workflow_state_includes_execution_events_after_run() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "workflow-state-lifecycle"
    manager.create_task(task_id)
    for engineering_input in sample_inputs().values():
        manager.store_input(task_id, engineering_input)

    execute_workflow(
        task_id,
        "pipe_wall_thickness_design",
        state=manager,
        reader=reader,
    )

    workflow_state = manager.get_workflow_state(task_id, reader=reader)
    payload = json_safe(workflow_state)
    assert payload["version"] == "6"
    assert payload["presentation_blocks"]
    assert payload["execution_events"]
    assert payload["execution_events"][0]["event"] == "beforeEnter"
