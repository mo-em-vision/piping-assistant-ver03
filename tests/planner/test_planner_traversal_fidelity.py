"""Tests for planner traversal fidelity on real engineering plans."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.planner_debug_projection import build_planner_debug_projection
from engine.planner.planner_traversal import build_planner_traversal_state_from_plan
from engine.reference.parameter_keys import param_node_id_for_input
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.planner.helpers import _reader
from tests.planner.plan_contract import REQ_REQUIRED_WALL_THICKNESS


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("traversal-fidelity-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def test_fresh_plan_current_node_is_gate_not_equation_output() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
    assert plan is not None
    assert plan.traversal is not None

    assert plan.traversal.current_active_node_id == param_node_id_for_input("straight_pipe_section")
    assert plan.traversal.current_active_node_id != param_node_id_for_input("required_wall_thickness")

    projection = build_planner_debug_projection(plan, reader=_reader())
    assert projection["current_node"]["node_id"] == param_node_id_for_input("straight_pipe_section")
    assert projection["current_node"]["display_name"] == param_node_id_for_input("straight_pipe_section")


def test_pipe_wall_plan_includes_equation_awaiting_parameter_gathering() -> None:
    manager, task = _fresh_pipe_wall_task()
    manager.store_fact(
        task.task_id,
        fact_from_engineering_input(
            straight_section_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    manager.store_fact(
        task.task_id,
        fact_from_engineering_input(
            internal_pressure_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    plan = build_engineering_plan(task, _reader())
    assert plan is not None

    eq_req = plan.requirements.get(REQ_REQUIRED_WALL_THICKNESS)
    assert eq_req is not None
    equation_id = str((eq_req.resolution or {}).get("source_node_id") or "")

    projection = build_planner_debug_projection(plan, reader=_reader())
    queue_ids = {item["node_id"] for item in projection["groups"]["queue_leaf_nodes"]}
    assert equation_id in queue_ids

    equation_row = next(
        row for row in projection["groups"]["queue_leaf_nodes"] if row["node_id"] == equation_id
    )
    assert equation_row["status_reason"] == "awaiting parameter gathering"


def test_rebuilt_traversal_emits_parameter_resolved_events() -> None:
    manager, task = _fresh_pipe_wall_task()
    manager.store_fact(
        task.task_id,
        fact_from_engineering_input(
            straight_section_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    plan = build_engineering_plan(task, _reader())
    assert plan is not None

    rebuilt = build_planner_traversal_state_from_plan(plan, reader=_reader())
    assert rebuilt is not None
    resolved_types = [event.event_type for event in rebuilt.traversal_events]
    assert "parameter_resolved" in resolved_types

    projection = build_planner_debug_projection(plan, reader=_reader())
    visited = projection["groups"]["visited_previous_step"]
    assert visited
    assert visited[0]["node_id"] == param_node_id_for_input("straight_pipe_section")
