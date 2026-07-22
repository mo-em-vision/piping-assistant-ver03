"""Tests for graph-derived missing input resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.navigation.task_missing_inputs import missing_inputs_for_task, resolve_task_workflow_id
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath(
        "knowledge", "standards", "asme", "asme_b31.3"
    ).exists(),
    reason="ASME B31.3 pack required",
)
def test_missing_inputs_for_task_pipe_wall_from_graph(project_root: Path) -> None:
    from engine.reference.standards_reader import StandardsReader

    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("missing-inputs-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_THICKNESS_DESIGN

    missing = missing_inputs_for_task(task, reader=reader)

    assert missing
    assert "straight_pipe_section" in missing or "pressure_design_case" in missing


def test_resolve_task_workflow_id_from_task_id() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-design-abc", status=TaskStatus.AWAITING_INPUT)

    assert resolve_task_workflow_id(task) == PIPE_WALL_THICKNESS_DESIGN


def test_resolve_task_workflow_id_prefers_outputs() -> None:
    manager = TaskStateManager()
    task = manager.create_task("generic-task", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN

    assert resolve_task_workflow_id(task) == MAWP_DESIGN
