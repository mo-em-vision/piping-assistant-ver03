"""Generic build_display_outputs pipeline — workflow-agnostic block ids."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus

from api.output_blocks import build_display_outputs
from tests.helpers.goals import task_with_planning


def test_generic_pipeline_emits_stable_preview_id_without_workflow_literals(
    standards_reader,
) -> None:
    manager = TaskStateManager()
    task = manager.create_task("generic-preview", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "formula_parameters",
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    task.active_nodes = ["304.1.2-a"]

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = [str(block.get("id") or "") for block in blocks]

    assert not any("pipe_wall" in block_id for block_id in ids)
    assert not any(
        block_id in {"minimum-thickness-equation", "pipe-schedule-recommendation"}
        for block_id in ids
    )
    assert any(block_id.startswith("path-preview-equation-") for block_id in ids)
