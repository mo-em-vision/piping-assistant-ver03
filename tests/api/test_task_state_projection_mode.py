"""Tests for interactive vs full task_state projection modes."""

from __future__ import annotations

from api.serializers import task_state
from engine.inspection.builder import build_inspection_payload
from engine.planner.goal_builder import build_goal_tree
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


def _reader() -> StandardsReader:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("projection-mode-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    reader = _reader()
    build_goal_tree(task, reader)
    manager.replace_task(task.task_id, task)
    return manager, task, reader


def test_interactive_task_state_omits_debug_projections() -> None:
    manager, task, reader = _fresh_pipe_wall_task()

    payload = task_state(task, manager, reader=reader, projection_mode="interactive")

    assert payload.get("task_id") == task.task_id
    assert isinstance(payload.get("parameters"), list)
    assert isinstance(payload.get("display_outputs"), list)
    assert isinstance(payload.get("flow_guidance"), dict)
    assert "engineering_plan" not in payload
    assert "engineering_plan_view" not in payload
    assert "legacy_goal_map" not in payload
    assert "canonical" not in payload
    assert "inspector_summary" not in payload


def test_full_task_state_includes_debug_projections() -> None:
    manager, task, reader = _fresh_pipe_wall_task()

    payload = task_state(task, manager, reader=reader, projection_mode="full")

    assert isinstance(payload.get("engineering_plan"), dict)
    assert isinstance(payload.get("engineering_plan_view"), dict)
    assert isinstance(payload.get("legacy_goal_map"), dict)
    assert isinstance(payload.get("canonical"), dict)
    assert isinstance(payload.get("inspector_summary"), dict)


def test_inspection_endpoint_still_includes_full_debug_payload() -> None:
    manager, task, reader = _fresh_pipe_wall_task()

    payload = build_inspection_payload(task, manager=manager, reader=reader)

    assert isinstance(payload.get("engineering_plan"), dict)
    assert isinstance(payload.get("planner_inspector_summary"), dict)
    assert isinstance(payload.get("planner_debug_projection"), dict)
    assert isinstance(payload.get("legacy_goal_map"), dict)
    assert isinstance(payload.get("canonical_task_state"), dict)
    assert isinstance(payload.get("task_state_views"), dict)
