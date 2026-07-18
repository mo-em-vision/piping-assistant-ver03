"""Tests for planner traversal state on engineering plans."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.plan_inspector import build_planner_inspector_summary
from engine.planner.plan_validation import validate_engineering_plan
from engine.planner.planner_traversal import build_planner_traversal_inspector_view
from engine.reference.parameter_keys import param_node_id_for_input
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.planner.helpers import _reader
from tests.planner.plan_contract import WELD_W_FIELD


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("traversal-fresh-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def test_fresh_pipe_wall_traversal_state() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    assert plan.traversal is not None

    traversal = plan.traversal
    straight_param = param_node_id_for_input("straight_pipe_section")
    assert traversal.current_active_node_id == straight_param
    assert traversal.current_active_node is not None
    assert traversal.current_active_node.node_id == straight_param
    assert traversal.current_active_node.phase == "expansion_assumptions"

    pending_ids = {item.node_id for item in traversal.pending_expansion_nodes}
    pending_node_ids = [item.node_id for item in traversal.pending_expansion_nodes]
    assert len(pending_node_ids) == len(set(pending_node_ids))
    assert param_node_id_for_input("pressure_design_case") in pending_ids
    assert "304.1.2-a" in pending_ids
    assert "304.1.3" not in pending_ids
    assert len(traversal.pending_expansion_nodes) == 2

    assert traversal.current_active_node is not None
    assert traversal.current_active_node.title == "Straight Pipe Section"

    pressure_pending = next(
        item
        for item in traversal.pending_expansion_nodes
        if item.node_id == param_node_id_for_input("pressure_design_case")
    )
    assert param_node_id_for_input("straight_pipe_section") in pressure_pending.waiting_on

    branch_pending = next(item for item in traversal.pending_expansion_nodes if item.node_id == "304.1.2-a")
    assert branch_pending.title == "Straight Pipe Under Internal Pressure"
    assert param_node_id_for_input("pressure_design_case") in branch_pending.waiting_on

    expanded_ids = {item.node_id for item in traversal.expanded_nodes}
    assert "WF-PIPE-WALL-THICKNESS" in expanded_ids
    assert expanded_ids.isdisjoint(pending_ids)
    workflow_expanded = next(
        item for item in traversal.expanded_nodes if item.node_id == "WF-PIPE-WALL-THICKNESS"
    )
    assert workflow_expanded.title in {
        "Pipe Wall Thickness Workflow",
        "Pipe Wall Thickness Design",
    }

    pressure_decision = next(item for item in traversal.branch_decisions if item.field == "pressure_design_case")
    assert pressure_decision.field == "pressure_design_case"
    assert pressure_decision.status == "unresolved"
    assert pressure_decision.value is None
    assert pressure_decision.selected_node is None
    assert pressure_decision.candidate_nodes == ["304.1.2-a", "304.1.3"]

    summary = build_planner_inspector_summary(plan)
    assert summary["traversal_summary"]["current_active_node_id"] == traversal.current_active_node_id
    assert summary["traversal_summary"]["pending_expansion_count"] == len(traversal.pending_expansion_nodes)
    assert summary["planner_traversal_view"] is not None

    view = build_planner_traversal_inspector_view(traversal)
    assert view["current_active_node"]["node_id"] == traversal.current_active_node_id
    assert view["recent_events"]


def test_traversal_active_node_follows_phase_order_after_straight_pipe() -> None:
    manager, task = _fresh_pipe_wall_task()
    manager.store_fact(
        task.task_id,
        fact_from_engineering_input(
            straight_section_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = manager.get_task(task.task_id)
    plan = build_engineering_plan(task, _reader())

    assert plan.traversal is not None
    pressure_param = param_node_id_for_input("pressure_design_case")
    assert plan.traversal.current_active_node_id == pressure_param
    assert plan.traversal.current_active_node is not None
    assert plan.traversal.current_active_node.node_id == pressure_param
    assert plan.traversal.current_active_node.phase == "path_decisions"

    coefficient_params = {
        param_node_id_for_input(field)
        for field in (
            "allowable_stress",
            "weld_joint_efficiency",
            "temperature_coefficient_Y",
            WELD_W_FIELD,
            "metallurgical_group",
        )
    }
    assert plan.traversal.current_active_node_id not in coefficient_params


def test_traversal_after_pressure_branch_resolved() -> None:
    manager, task = _fresh_pipe_wall_task()
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    task = manager.get_task(task.task_id)
    plan = build_engineering_plan(task, _reader())

    assert plan.traversal is not None
    assert plan.traversal.current_active_node is not None
    assert plan.traversal.current_active_node.phase == "parameter_gathering"
    internal_pressure_param = param_node_id_for_input("internal_design_gage_pressure")
    assert plan.traversal.current_active_node_id == internal_pressure_param
    assert plan.traversal.current_active_node.node_id == internal_pressure_param

    pending_ids = {item.node_id for item in plan.traversal.pending_expansion_nodes}
    assert "304.1.2-a" not in pending_ids
    assert "304.1.3" not in pending_ids

    pressure_decision = next(
        item for item in plan.traversal.branch_decisions if item.field == "pressure_design_case"
    )
    assert pressure_decision.status == "resolved"
    assert pressure_decision.value == "internal_pressure"
