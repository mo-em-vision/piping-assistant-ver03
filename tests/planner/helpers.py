"""Shared helpers for planner tests."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def fresh_pipe_wall_task(*, task_id: str = "planner-test-pwt"):
    manager = TaskStateManager()
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def gates_satisfied_pipe_wall_task(*, task_id: str = "planner-test-pwt-gates"):
    manager, task = fresh_pipe_wall_task(task_id=task_id)
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    return manager, manager.get_task(task.task_id)


def gates_open_pipe_wall_plan(*, task_id: str = "planner-test-pwt-gates"):
    """Build a pipe-wall plan after expansion and path gates are satisfied."""
    from engine.planner.engineering_plan_builder import build_engineering_plan
    from engine.planner.tools import GraphTools

    _, task = gates_satisfied_pipe_wall_task(task_id=task_id)
    reader = _reader()
    graph = GraphTools(reader)
    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.fact_store.active_facts()),
    )
    return build_engineering_plan(
        task,
        reader,
        preview=preview,
        existing_inputs=dict(task.fact_store.active_facts()),
    )
