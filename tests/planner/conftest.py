"""Shared planner test helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def fresh_pipe_wall_task(
    *,
    task_id: str = "planner-test-pwt",
    manager: TaskStateManager | None = None,
):
    state = manager or TaskStateManager()
    task = state.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return state, task


def build_plan(task, reader: StandardsReader, **kwargs):
    return build_engineering_plan(task, reader, **kwargs)
