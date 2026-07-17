"""Runtime workflow state boundary tests."""

from __future__ import annotations

import json
from pathlib import Path

from api.json_encoding import json_safe
from engine.executor.executor import execute_workflow
from engine.reference.standards_reader import StandardsReader
from engine.state import TaskStateManager
from models.execution import ExecutionStatus
from tests.acceptance.helpers import (
    PIPE_WALL_THICKNESS_ROOT,
    create_task_with_inputs,
)
from tests.helpers.facts import legacy_input, set_fact_from_input


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_workflow_state_is_serializable_runtime_data() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "workflow-state-boundary"
    manager.create_task(task_id)
    task = manager.get_task(task_id)
    set_fact_from_input(
        task,
        legacy_input(
            input_id="internal_design_gage_pressure",
            value=500,
            unit="psi",
        ),
    )
    manager.replace_task(task_id, task)
    manager.store_output(task_id, "workflow", "pipe_wall_thickness_design")
    manager.store_output(task_id, "required_thickness", 0.084)
    manager.store_output(
        task_id,
        "allowable_stress_lookup",
        {"table": "A-1", "value": 193_000_000.0, "unit": "Pa"},
    )
    manager.store_output(task_id, "graph_version", {"nodes": ["304.1.2-a"]})
    manager.store_output(
        task_id,
        "_execution_trace",
        [
            {"node_id": "asme-b313-table-A-1", "status": "completed"},
            {"node_id": "304.1.2-a", "status": "completed"},
        ],
    )
    manager.add_warning(task_id, "Review corrosion allowance.")
    manager.store_step_progress(task_id, "asme-b313-table-A-1", "completed")
    manager.store_step_progress(task_id, "304.1.2-a", "completed")

    workflow_state = manager.get_workflow_state(task_id, reader=reader)
    payload = json_safe(workflow_state)

    json.dumps(payload)
    assert payload["task_id"] == task_id
    assert payload["workflow_id"] == "pipe_wall_thickness_design"
    assert payload["visited_nodes"] == ["asme-b313-table-A-1", "304.1.2-a"]
    assert payload["variable_values"]["internal_design_gage_pressure"]["value"] == 500
    assert payload["variable_values"]["required_thickness"] == 0.084
    assert payload["lookup_results"]["allowable_stress_lookup"]["value"] == 193_000_000.0
    assert "graph_version" not in payload["variable_values"]
    assert payload["warnings"] == ["Review corrosion allowance."]
    assert payload["version"] == "5"
    assert payload["presentation_blocks"]
    assert "node_outputs" in payload
    assert any(block["type"] == "warning" for block in payload["presentation_blocks"])
    assert payload["parameters"]["internal_design_gage_pressure"]["param_node_id"] == "PARAM-internal-design-gage-pressure"
    assert payload["parameters"]["internal_design_gage_pressure"]["source"] == "user_input"
    pressure = payload["parameters"]["internal_design_gage_pressure"]
    assert pressure["canonical_unit"] == "UNIT-Pa"
    assert "UNIT-psi" in pressure["allowed_units"]
    assert pressure["unit_id"] == "UNIT-psi"


def test_workflow_state_includes_execution_events_after_run() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "workflow-state-lifecycle"
    create_task_with_inputs(manager, task_id)
    result = execute_workflow(
        task_id,
        PIPE_WALL_THICKNESS_ROOT,
        state=manager,
        reader=reader,
    )
    assert result.status == ExecutionStatus.COMPLETED

    workflow_state = manager.get_workflow_state(task_id, reader=reader)
    payload = json_safe(workflow_state)
    assert payload["version"] == "6"
    assert payload["presentation_blocks"]
    assert payload["execution_events"]
    assert payload["execution_events"][0]["event"] == "beforeEnter"
