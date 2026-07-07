"""Tests that MAWP planner path stays graph-driven without hardcoded branches."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.goal_builder import build_goal_tree
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from tests.graph.conftest import MAWP_ROOT, mawp_gate_open_inputs


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath(
        "knowledge", "standards", "asme", "asme_b31.3"
    ).exists(),
    reason="ASME B31.3 pack required",
)
def test_mawp_engineering_plan_returns_none(project_root: Path) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("mawp-plan-test")
    task.outputs["workflow"] = MAWP_ROOT
    for key, fact in mawp_gate_open_inputs(task_id=task.task_id).items():
        manager.store_input(task.task_id, fact)

    plan = build_engineering_plan(task, reader)
    assert plan is None


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath(
        "knowledge", "standards", "asme", "asme_b31.3"
    ).exists(),
    reason="ASME B31.3 pack required",
)
def test_mawp_goal_tree_builds_via_generic_path(project_root: Path) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("mawp-goal-test")
    task.outputs["workflow"] = MAWP_ROOT
    for key, fact in mawp_gate_open_inputs(task_id=task.task_id).items():
        manager.store_input(task.task_id, fact)

    goals = build_goal_tree(task, reader)
    assert goals.roots() or goals.goals
