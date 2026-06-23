"""Tests for desktop display output blocks."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus

from api.output_blocks import build_display_outputs
from api.serializers import task_state
from tests.acceptance.helpers import run_completed_workflow


def test_preview_outputs_for_awaiting_input_task() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test06", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "goal": "pipe wall thickness design",
            "action": "request_input",
            "missing_inputs": ["material", "design_pressure"],
            "missing_assumptions": [],
        },
    }
    manager.replace_task(task.task_id, task)

    blocks = build_display_outputs(task)
    types = {block["type"] for block in blocks}

    assert "text" in types
    assert "equation" in types
    assert "table" in types
    assert "reference" in types


def test_completed_workflow_outputs_include_results_and_equation(
    standards_reader,
    state_manager,
) -> None:
    task_id = "pipe-wall-thickness-desi-test07"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)

    blocks = build_display_outputs(task)
    types = [block["type"] for block in blocks]

    assert "result" in types
    assert "equation" in types
    assert any(block["type"] == "table" for block in blocks)


def test_task_state_includes_display_outputs(
    standards_reader,
    state_manager,
) -> None:
    task_id = "pipe-wall-thickness-desi-test08"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)

    state = task_state(task, state_manager)
    assert isinstance(state["display_outputs"], list)
    assert len(state["display_outputs"]) > 0
