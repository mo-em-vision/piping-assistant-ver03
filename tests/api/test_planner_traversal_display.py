"""Tests for planner-traversal-driven center panel display blocks."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.output_blocks import build_display_outputs
from api.planner_traversal_display import (
    build_display_blocks_for_traversal_node,
    collect_traversal_display_nodes,
)
from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.legacy_goal_adapter import store_engineering_plan_on_task
from engine.planner.plan_selection import engineering_plan_for_task
from engine.reference.standards_reader import StandardsReader
from engine.router import MAWP_DESIGN
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import (
    CalculationGoal,
    EngineeringPlan,
    PlannerTraversalState,
    TraversalActiveNode,
    TraversalExpandedNode,
    TraversalPendingNode,
)
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.graph.conftest import mawp_gate_open_inputs
from tests.helpers.planner_traversal import store_synthetic_traversal_plan

MAWP_EQ_ID = "asme-b313-mawp-pressure"
EQ_3A_ID = "asme-b313-304-1-2-eq-3a"
PARAGRAPH_ID = "304.1.2-a"


def _reader(project_root: Path | None = None) -> StandardsReader:
    root = project_root or Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _store_traversal_plan(
    task,
    *,
    expanded: list[TraversalExpandedNode] | None = None,
    pending: list[TraversalPendingNode] | None = None,
    active: TraversalActiveNode | None = None,
    workflow_id: str | None = None,
) -> None:
    store_synthetic_traversal_plan(
        task,
        expanded=expanded,
        pending=pending,
        active=active,
        workflow_id=workflow_id,
    )


def test_collect_traversal_display_nodes_orders_expanded_then_pending() -> None:
    plan = EngineeringPlan(
        plan_id="PLAN-order",
        task_id="task-order",
        workflow_id="pipe_wall_thickness_design",
        root_goal=CalculationGoal(id="GOAL-order", key="order", title="Order"),
        traversal=PlannerTraversalState(
            traversal_id="TRAV-order",
            expanded_nodes=[
                TraversalExpandedNode("para-b", "paragraph", expanded_at_order=2),
                TraversalExpandedNode("para-a", "paragraph", expanded_at_order=1),
            ],
            pending_expansion_nodes=[
                TraversalPendingNode("eq-pending", "equation", waiting_on=[], reason="test"),
            ],
            current_active_node=TraversalActiveNode(
                "PARAM-test",
                "parameter",
                reason="active ask",
            ),
        ),
    )

    nodes = collect_traversal_display_nodes(plan)
    assert [item.node_id for item in nodes] == ["para-a", "para-b", "eq-pending"]
    assert all(item.node_type != "parameter" for item in nodes)


def test_collect_traversal_display_nodes_skips_workflow_and_parameter() -> None:
    plan = EngineeringPlan(
        plan_id="PLAN-skip",
        task_id="task-skip",
        workflow_id="mawp_design",
        root_goal=CalculationGoal(id="GOAL-skip", key="skip", title="Skip"),
        traversal=PlannerTraversalState(
            traversal_id="TRAV-skip",
            expanded_nodes=[
                TraversalExpandedNode("mawp_design", "workflow", expanded_at_order=1),
            ],
            pending_expansion_nodes=[
                TraversalPendingNode("PARAM-test", "parameter", waiting_on=[], reason="ask"),
            ],
        ),
    )

    assert collect_traversal_display_nodes(plan) == []


def test_build_display_blocks_for_paragraph_and_equation(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("traversal-dispatch", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    paragraph_blocks = build_display_blocks_for_traversal_node(
        standards_reader,
        task,
        PARAGRAPH_ID,
        "paragraph",
    )
    assert len(paragraph_blocks) == 1
    assert paragraph_blocks[0]["type"] == "paragraph_context"
    assert paragraph_blocks[0]["id"] == f"paragraph-{PARAGRAPH_ID}"

    equation_blocks = build_display_blocks_for_traversal_node(
        standards_reader,
        task,
        EQ_3A_ID,
        "equation",
    )
    assert len(equation_blocks) == 1
    assert equation_blocks[0]["type"] == "equation"
    assert equation_blocks[0]["equation_node_id"] == EQ_3A_ID


def test_build_display_outputs_uses_pending_traversal_equation(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("traversal-display", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN
    _store_traversal_plan(
        task,
        pending=[
            TraversalPendingNode(
                MAWP_EQ_ID,
                "equation",
                waiting_on=["internal_design_gage_pressure"],
                reason="pending equation",
            )
        ],
    )

    blocks = build_display_outputs(task, reader=standards_reader)
    equation_ids = [
        str(block.get("id"))
        for block in blocks
        if str(block.get("type") or "") == "equation"
    ]
    assert f"equation-{MAWP_EQ_ID}" in equation_ids


def test_mawp_engineering_plan_pending_equation_renders_in_display_outputs(
    project_root: Path,
) -> None:
    reader = _reader(project_root)
    manager = TaskStateManager()
    task = manager.create_task("mawp-traversal-display", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN
    task.outputs["selected_root"] = MAWP_DESIGN
    for fact in mawp_gate_open_inputs(task_id=task.task_id).values():
        manager.store_fact(task.task_id, fact)
    task = manager.get_task(task.task_id)

    plan = build_engineering_plan(task, reader)
    store_engineering_plan_on_task(task, plan)
    activated_equation_ids = [
        item.node_id
        for item in collect_traversal_display_nodes(plan)
        if item.node_type == "equation"
    ]
    assert MAWP_EQ_ID in activated_equation_ids

    blocks = build_display_outputs(task, reader=reader)
    equation_block_ids = {
        str(block.get("id"))
        for block in blocks
        if str(block.get("type") or "") == "equation"
    }
    assert f"equation-{MAWP_EQ_ID}" in equation_block_ids


def test_pipe_wall_traversal_paragraph_block_without_focus_heuristic(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("traversal-paragraph", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
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
    _store_traversal_plan(
        task,
        expanded=[
            TraversalExpandedNode(PARAGRAPH_ID, "paragraph", expanded_at_order=1),
        ],
        pending=[
            TraversalPendingNode(EQ_3A_ID, "equation", waiting_on=[], reason="preview"),
        ],
    )

    blocks = build_display_outputs(task, reader=standards_reader)
    block_ids = {str(block.get("id")) for block in blocks}
    assert f"paragraph-{PARAGRAPH_ID}" in block_ids
    assert f"equation-{EQ_3A_ID}" in block_ids

    plan = engineering_plan_for_task(task)
    assert plan is not None
    assert collect_traversal_display_nodes(plan)
