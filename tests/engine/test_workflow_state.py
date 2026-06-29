"""Runtime workflow state boundary tests."""

from __future__ import annotations

import json

from api.json_encoding import json_safe
from engine.state import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus


def test_workflow_state_is_serializable_runtime_data() -> None:
    manager = TaskStateManager()
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

    workflow_state = manager.get_workflow_state(task_id)
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
