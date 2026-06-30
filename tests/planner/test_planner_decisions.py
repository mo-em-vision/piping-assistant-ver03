"""Planner decision records for developer inspection."""

from __future__ import annotations

from engine.inspection.planner_decisions import build_planner_decisions
from models.execution import ExecutionPlan
from models.graph import EdgeType, GraphEdge


def test_build_planner_decisions_for_execution_order() -> None:
    plan = ExecutionPlan(
        task_id="task-1",
        root="wf-root",
        nodes=("a", "b", "c"),
        execution_order=("a", "b", "c"),
        dependencies=(
            GraphEdge("a", "b", EdgeType.REQUIRES),
            GraphEdge("b", "c", EdgeType.REQUIRES),
        ),
        skipped_nodes=({"node_id": "legacy", "reason": "invalid edition"},),
    )
    decisions = build_planner_decisions(plan)
    assert "a" in decisions
    assert "b" in decisions
    assert decisions["b"].trigger_dependency == "a"
    assert decisions["legacy"].why_selected == "invalid edition"
