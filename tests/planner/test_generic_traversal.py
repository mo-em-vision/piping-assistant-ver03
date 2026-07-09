"""Tests for workflow-agnostic planner traversal and engineering plan assembly."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.planner_debug_projection import build_planner_debug_projection
from engine.planner.planner_traversal import build_planner_traversal_state_from_plan
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.graph.conftest import MAWP_ROOT, mawp_gate_open_inputs


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath(
        "knowledge", "standards", "asme", "asme_b31.3"
    ).exists(),
    reason="ASME B31.3 pack required",
)
def test_mawp_plan_has_populated_generic_traversal(project_root: Path) -> None:
    reader = _reader(project_root)
    manager = TaskStateManager()
    task = manager.create_task("generic-traversal-mawp", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_ROOT
    for key, fact in mawp_gate_open_inputs(task_id=task.task_id).items():
        manager.store_input(task.task_id, fact)

    plan = build_engineering_plan(task, reader)
    assert plan is not None
    assert plan.traversal is not None

    traversal = plan.traversal
    assert traversal.current_active_node_id is not None
    assert traversal.expanded_nodes
    assert traversal.branch_decisions is not None

    projection = build_planner_debug_projection(plan, reader=reader)
    assert projection["current_node"] is not None
    assert projection["goals"]["main_goal"]
    groups = projection["groups"]
    assert groups["visited_from_beginning"]


@pytest.mark.skipif(
    not Path(__file__).resolve().parents[2].joinpath(
        "knowledge", "standards", "asme", "asme_b31.3"
    ).exists(),
    reason="ASME B31.3 pack required",
)
def test_rebuilt_traversal_matches_persisted_plan(project_root: Path) -> None:
    reader = _reader(project_root)
    manager = TaskStateManager()
    task = manager.create_task("generic-traversal-rebuild", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_ROOT
    for key, fact in mawp_gate_open_inputs(task_id=task.task_id).items():
        manager.store_input(task.task_id, fact)

    plan = build_engineering_plan(task, reader)
    assert plan is not None

    rebuilt = build_planner_traversal_state_from_plan(plan, reader=reader)
    assert rebuilt is not None
    assert rebuilt.current_active_node_id == plan.traversal.current_active_node_id
    assert len(rebuilt.pending_expansion_nodes) == len(plan.traversal.pending_expansion_nodes)


def test_traversal_builder_returns_none_without_workflow_id() -> None:
    from engine.planner.planner_traversal import build_planner_traversal_state
    from models.engineering_plan import PlanGraph, new_plan_id

    state = build_planner_traversal_state(
        plan_id=new_plan_id(),
        workflow_id="",
        requirements={},
        input_strategy=None,
        graph=PlanGraph(),
    )
    assert state is None
