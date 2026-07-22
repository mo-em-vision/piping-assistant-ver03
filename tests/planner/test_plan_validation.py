"""Tests for engineering plan validation invariants."""

from __future__ import annotations

from copy import deepcopy

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.plan_validation import validate_engineering_plan
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import PlanDependency, TraversalExpandedNode
from models.task import TaskStatus
from tests.planner.helpers import _reader


from tests.planner.test_plan_requirements import _gates_satisfied_task


def _gates_open_plan():
    _, task = _gates_satisfied_task()
    return build_engineering_plan(task, _reader())


def _fresh_plan():
    state = TaskStateManager()
    task = state.create_task("plan-validation", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    return build_engineering_plan(task, _reader())


def test_validate_rejects_resolution_branch_as_lookup_input_source() -> None:
    plan = _gates_open_plan()
    resolution_id = next(
        req_id
        for req_id, req in plan.requirements.items()
        if req.alternatives and req.field == "outside_diameter"
    )
    lookup_id = "REQ-outside_diameter_lookup"
    plan.dependencies.append(
        PlanDependency(
            from_id=resolution_id,
            to_id=lookup_id,
            type="lookup_input",
        )
    )
    result = validate_engineering_plan(plan)
    assert not result.valid
    assert any(resolution_id in error for error in result.errors)


def test_validate_rejects_diameter_resolution_as_lookup_input_source() -> None:
    plan = _fresh_plan()
    plan.dependencies.append(
        PlanDependency(
            from_id="REQ-diameter_resolution",
            to_id="REQ-outside_diameter_lookup",
            type="lookup_input",
        )
    )
    result = validate_engineering_plan(plan)
    assert not result.valid
    assert any("REQ-diameter_resolution" in error for error in result.errors)


def test_validate_accepts_nominal_pipe_size_lookup_input_edge() -> None:
    plan = _gates_open_plan()
    result = validate_engineering_plan(plan)
    assert result.valid, result.errors
    assert any(
        edge.from_id == "REQ-nominal_pipe_size"
        and edge.to_id == "REQ-outside_diameter_lookup"
        and edge.type == "lookup_input"
        for edge in plan.dependencies
    )


def test_validate_rejects_duplicate_pending_expansion_nodes() -> None:
    plan = _fresh_plan()
    assert plan.traversal is not None
    duplicate = deepcopy(plan.traversal.pending_expansion_nodes[0])
    plan.traversal.pending_expansion_nodes.append(duplicate)

    result = validate_engineering_plan(plan)
    assert not result.valid
    assert any("duplicate node ids" in error for error in result.errors)


def test_validate_rejects_pending_and_expanded_node_overlap() -> None:
    plan = _fresh_plan()
    assert plan.traversal is not None
    pending = plan.traversal.pending_expansion_nodes[0]
    plan.traversal.expanded_nodes.append(
        TraversalExpandedNode(
            node_id=pending.node_id,
            node_type=pending.node_type,
            expanded_at_order=len(plan.traversal.expanded_nodes) + 1,
            title=pending.title,
        )
    )

    result = validate_engineering_plan(plan)
    assert not result.valid
    assert any("overlap" in error for error in result.errors)


def test_validate_rejects_branch_candidate_active_before_decision_resolved() -> None:
    plan = _fresh_plan()
    assert plan.traversal is not None
    from models.engineering_plan import TraversalBranchDecision

    plan.traversal.branch_decisions = [
        TraversalBranchDecision(
            field="pressure_design_case",
            value=None,
            selected_node=None,
            candidate_nodes=["304.1.2-a"],
            status="unresolved",
        )
    ]
    plan.traversal.current_active_node_id = "304.1.2-a"

    result = validate_engineering_plan(plan)
    assert not result.valid
    assert any("is active before branch" in error for error in result.errors)


def test_validate_rejects_branch_candidate_expanded_before_decision_resolved() -> None:
    plan = _fresh_plan()
    assert plan.traversal is not None
    from models.engineering_plan import TraversalBranchDecision

    plan.traversal.branch_decisions = [
        TraversalBranchDecision(
            field="pressure_design_case",
            value=None,
            selected_node=None,
            candidate_nodes=["304.1.2-a"],
            status="unresolved",
        )
    ]
    plan.traversal.expanded_nodes.append(
        TraversalExpandedNode(
            node_id="304.1.2-a",
            node_type="calculation",
            expanded_at_order=len(plan.traversal.expanded_nodes) + 1,
            title="Straight Pipe Under Internal Pressure",
        )
    )

    result = validate_engineering_plan(plan)
    assert not result.valid
    assert any("is expanded before branch" in error for error in result.errors)
