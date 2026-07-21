"""Test helpers for injecting planner traversal into tasks."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.legacy_goal_adapter import store_engineering_plan_on_task
from engine.reference.standards_reader import StandardsReader
from models.engineering_plan import (
    CalculationGoal,
    EngineeringPlan,
    PlannerTraversalState,
    TraversalActiveNode,
    TraversalExpandedNode,
    TraversalPendingNode,
)
from models.task import Task


def store_synthetic_traversal_plan(
    task: Task,
    *,
    expanded: list[TraversalExpandedNode] | None = None,
    pending: list[TraversalPendingNode] | None = None,
    active: TraversalActiveNode | None = None,
    workflow_id: str | None = None,
) -> EngineeringPlan:
    wf = workflow_id or str(task.outputs.get("workflow") or "pipe_wall_thickness_design")
    plan = EngineeringPlan(
        plan_id="PLAN-traversal-test",
        task_id=task.task_id,
        workflow_id=wf,
        root_goal=CalculationGoal(id="GOAL-test", key="test", title="Test goal"),
        traversal=PlannerTraversalState(
            traversal_id="TRAV-test",
            current_active_node_id=active.node_id if active else None,
            current_active_node=active,
            expanded_nodes=expanded or [],
            pending_expansion_nodes=pending or [],
        ),
    )
    store_engineering_plan_on_task(task, plan)
    return plan


def store_built_engineering_plan(task: Task, reader: StandardsReader) -> EngineeringPlan:
    plan = build_engineering_plan(task, reader)
    store_engineering_plan_on_task(task, plan)
    return plan
