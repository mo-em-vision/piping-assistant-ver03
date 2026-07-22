"""Tests for planner traversal fidelity on real engineering plans."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.planner_debug_projection import build_planner_debug_projection
from engine.planner.planner_traversal import build_planner_traversal_state_from_plan
from engine.planner.tools import GraphTools
from engine.reference.parameter_keys import param_node_id_for_input
from engine.state.fact_migration import fact_from_engineering_input
from tests.acceptance.helpers import straight_section_assumption
from tests.planner.helpers import _reader, fresh_pipe_wall_task, gates_satisfied_pipe_wall_task


def test_fresh_plan_current_node_is_gate_not_equation_output() -> None:
    _, task = fresh_pipe_wall_task(task_id="traversal-fidelity-pwt")
    plan = build_engineering_plan(task, _reader())
    assert plan is not None
    assert plan.traversal is not None

    assert plan.traversal.current_active_node_id == param_node_id_for_input("straight_pipe_section")
    assert plan.traversal.current_active_node_id != param_node_id_for_input("required_wall_thickness")

    projection = build_planner_debug_projection(plan, reader=_reader())
    assert projection["current_node"]["node_id"] == param_node_id_for_input("straight_pipe_section")
    assert projection["current_node"]["display_name"] == param_node_id_for_input("straight_pipe_section")


def test_gates_open_plan_queues_parameter_gathering_nodes() -> None:
    _, task = gates_satisfied_pipe_wall_task(task_id="traversal-fidelity-gates")
    graph = GraphTools(_reader())
    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.fact_store.active_facts()),
    )
    plan = build_engineering_plan(
        task,
        _reader(),
        preview=preview,
        existing_inputs=dict(task.fact_store.active_facts()),
    )
    assert plan is not None

    projection = build_planner_debug_projection(plan, reader=_reader())
    queue_ids = {item["node_id"] for item in projection["groups"]["queue_leaf_nodes"]}
    assert param_node_id_for_input("internal_design_gage_pressure") in queue_ids
    assert projection["current_node"]["node_id"] == param_node_id_for_input("design_temperature")

    temperature_row = next(
        row
        for row in projection["groups"]["queue_leaf_nodes"]
        if row["node_id"] == param_node_id_for_input("internal_design_gage_pressure")
    )
    assert temperature_row["status_reason"] == "waiting_for_dependency"


def test_rebuilt_traversal_emits_node_expanded_events() -> None:
    manager, task = fresh_pipe_wall_task(task_id="traversal-fidelity-events")
    manager.store_fact(
        task.task_id,
        fact_from_engineering_input(
            straight_section_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = manager.get_task(task.task_id)
    plan = build_engineering_plan(task, _reader(), existing_inputs=dict(task.fact_store.active_facts()))
    assert plan is not None

    rebuilt = build_planner_traversal_state_from_plan(plan, reader=_reader())
    assert rebuilt is not None
    event_types = [event.event_type for event in rebuilt.traversal_events]
    assert "node_expanded" in event_types

    projection = build_planner_debug_projection(plan, reader=_reader())
    visited = projection["groups"]["visited_previous_step"]
    assert visited
    assert visited[0]["node_id"]
