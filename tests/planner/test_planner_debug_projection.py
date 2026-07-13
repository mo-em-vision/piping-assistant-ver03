"""Tests for read-only planner_debug_projection minimal debugger view."""

from __future__ import annotations

import pytest

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.planner_debug_projection import (
    _STATUS_REASONS,
    build_planner_debug_projection,
    planner_debug_projection_for_task,
)
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import (
    CalculationGoal,
    EngineeringPlan,
    InputStrategy,
    PlanGraph,
    PlanPhase,
    PlanRequirement,
    PlannerTraversalState,
    QuestionSpec,
    TraversalActiveNode,
    TraversalCandidateNode,
    TraversalEvent,
    TraversalExpandedNode,
    TraversalPendingNode,
    new_plan_id,
)
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.planner.helpers import _reader, fresh_pipe_wall_task


_LIVE_DEBUG_GROUP_KEYS = (
    "visited_from_beginning",
    "visited_previous_step",
    "queue_leaf_nodes",
)


def _live_projection_node_refs(projection: dict) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    current = projection.get("current_node")
    if isinstance(current, dict) and current.get("node_id"):
        refs.append(("current_node", str(current["node_id"])))

    groups = projection.get("groups") or {}
    for group_name in _LIVE_DEBUG_GROUP_KEYS:
        for item in groups.get(group_name) or []:
            if isinstance(item, dict) and item.get("node_id"):
                refs.append((group_name, str(item["node_id"])))
    return refs


def assert_live_projection_groups_disjoint(projection: dict) -> None:
    seen: dict[str, str] = {}
    for group_name, node_id in _live_projection_node_refs(projection):
        prior = seen.get(node_id)
        if prior is not None:
            pytest.fail(
                f"node {node_id!r} appears in both {prior!r} and {group_name!r}"
            )
        seen[node_id] = group_name


def _pipe_wall_projection(stage: str) -> dict:
    manager, task = fresh_pipe_wall_task(task_id=f"debug-projection-pwt-{stage}")
    if stage in {"after_straight_pipe", "after_expansion_gates"}:
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                straight_section_assumption(),
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    if stage == "after_expansion_gates":
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                internal_pressure_assumption(),
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    task = manager.get_task(task.task_id)
    plan = build_engineering_plan(task, _reader())
    assert plan is not None
    return build_planner_debug_projection(plan, reader=_reader(), task=task)


@pytest.mark.parametrize(
    "stage",
    ("fresh", "after_straight_pipe", "after_expansion_gates"),
)
def test_pipe_wall_live_debug_groups_have_unique_node_ids(stage: str) -> None:
    projection = _pipe_wall_projection(stage)
    assert_live_projection_groups_disjoint(projection)


def _synthetic_generic_plan() -> EngineeringPlan:
    req = PlanRequirement(
        id="REQ-sample_input",
        field="sample_input",
        parameter_node_id="PARAM-sample-input",
        requirement_class="user_input",
        status="missing",
        phase="parameter_gathering",
        key="input-sample_input",
        title="Sample Input",
        question_spec=QuestionSpec(
            field="sample_input",
            label="Sample Input",
            expected_value_class="selection",
            priority=10,
            ask_policy="ask_now",
            reason_code="required_for_generic_workflow",
        ),
    )
    traversal = PlannerTraversalState(
        traversal_id="TRAV-synthetic",
        current_active_node_id="PARAM-sample-input",
        current_active_node=TraversalActiveNode(
            node_id="PARAM-sample-input",
            node_type="parameter",
            title="Sample Input",
            phase="parameter_gathering",
            reason="Active parameter on generic workflow path",
        ),
        expanded_nodes=[
            TraversalExpandedNode(
                node_id="WF-GENERIC",
                node_type="workflow",
                expanded_at_order=1,
                title="Generic Workflow",
            )
        ],
        pending_expansion_nodes=[
            TraversalPendingNode(
                node_id="NODE-pending",
                node_type="paragraph",
                waiting_on=["PARAM-sample-input"],
                reason="Blocked until sample input is provided",
                title="Pending Paragraph",
            )
        ],
    )
    return EngineeringPlan(
        plan_id=new_plan_id(),
        task_id="task-synthetic",
        workflow_id="generic_sample_workflow",
        root_goal=CalculationGoal(
            id="GOAL-sample",
            key="calculate-sample",
            title="Generic Sample Calculation",
            target_field="sample_output",
            status="blocked",
            required_outputs=["sample_output", "sample_report"],
        ),
        requirements={
            "REQ-sample_input": req,
            "REQ-sample_output": PlanRequirement(
                id="REQ-sample_output",
                field="sample_output",
                parameter_node_id=None,
                requirement_class="equation_result",
                status="missing",
                phase="calculation",
                key="equation-sample_output",
                title="Sample Output",
            ),
            "REQ-sample_report": PlanRequirement(
                id="REQ-sample_report",
                field="sample_report",
                parameter_node_id=None,
                requirement_class="report_output",
                status="missing",
                phase="reporting",
                key="report-sample_report",
                title="Sample Report",
            ),
        },
        input_strategy=InputStrategy(
            mode="sequential",
            current_phase="parameter_gathering",
            resolved_fields=[],
            blocked_fields=[],
            next_fields=["sample_input"],
        ),
        graph=PlanGraph(),
        phases=[],
        traversal=traversal,
        debug={"validation_warnings": [], "validation_errors": []},
    )


def _plan_with_multiple_expansions() -> EngineeringPlan:
    plan = _synthetic_generic_plan()
    assert plan.traversal is not None
    plan.traversal.expanded_nodes = [
        TraversalExpandedNode(
            node_id="WF-GENERIC",
            node_type="workflow",
            expanded_at_order=1,
            title="Generic Workflow",
        ),
        TraversalExpandedNode(
            node_id="NODE-first",
            node_type="paragraph",
            expanded_at_order=2,
            title="First Paragraph",
        ),
        TraversalExpandedNode(
            node_id="PARAM-sample-input",
            node_type="parameter",
            expanded_at_order=3,
            title="Sample Input",
        ),
    ]
    plan.traversal.current_active_node_id = "NODE-next"
    plan.traversal.current_active_node = TraversalActiveNode(
        node_id="NODE-next",
        node_type="paragraph",
        title="Next Paragraph",
        phase="calculation",
        reason="Active after sample input",
    )
    return plan


def _plan_with_excluded_event() -> EngineeringPlan:
    plan = _synthetic_generic_plan()
    assert plan.traversal is not None
    plan.traversal.traversal_events = [
        TraversalEvent(
            order=1,
            event_type="node_marked_not_applicable",
            node_id="NODE-excluded",
            message="Branch ruled out",
        )
    ]
    plan.traversal.pending_expansion_nodes.append(
        TraversalPendingNode(
            node_id="NODE-excluded",
            node_type="paragraph",
            waiting_on=[],
            reason="Not applicable on this branch",
            title="Excluded Paragraph",
        )
    )
    return plan


def _plan_with_phases_fallback() -> EngineeringPlan:
    plan = _synthetic_generic_plan()
    plan.root_goal.required_outputs = []
    plan.phases = [
        PlanPhase(id="phase_a", title="Gather Inputs", order=1),
        PlanPhase(id="phase_b", title="Run Calculation", order=2),
    ]
    return plan


def _plan_with_equation_gathering() -> EngineeringPlan:
    plan = _synthetic_generic_plan()
    assert plan.traversal is not None
    plan.traversal.pending_expansion_nodes = [
        TraversalPendingNode(
            node_id="asme-b313-304-1-2-eq-3a",
            node_type="equation",
            waiting_on=[],
            reason="Awaiting parameter gathering.",
            title="Internal Pressure Wall Thickness — Eq. (3a)",
            phase="equation_execution",
        ),
        TraversalPendingNode(
            node_id="PARAM-outside-diameter",
            node_type="parameter",
            waiting_on=[],
            reason="Awaiting user input.",
            phase="parameter_gathering",
            title="Outside Diameter",
        ),
    ]
    return plan


def test_projection_shape_contract() -> None:
    projection = build_planner_debug_projection(_synthetic_generic_plan())

    for key in ("current_node", "next_queued_node", "goals", "groups"):
        assert key in projection

    groups = projection["groups"]
    for key in (
        "visited_previous_step",
        "queue_leaf_nodes",
        "visited_from_beginning",
        "excluded_nodes",
        "blocked_nodes",
        "excluded_blocked",
    ):
        assert key in groups

    legacy_keys = (
        "workflow_slug",
        "visited_timeline",
        "pending_nodes",
        "required_inputs",
        "blocked_reason",
        "raw_planner_state",
    )
    for key in legacy_keys:
        assert key not in projection


def test_traversal_populated_groups() -> None:
    projection = build_planner_debug_projection(_synthetic_generic_plan())
    groups = projection["groups"]

    assert projection["current_node"]["node_id"] == "PARAM-sample-input"
    assert projection["current_node"]["display_name"] == "PARAM-sample-input"
    assert projection["next_queued_node"]["node_id"] == "NODE-pending"
    assert groups["visited_previous_step"]
    assert groups["queue_leaf_nodes"]
    assert groups["queue_leaf_nodes"][0]["status_reason"] in _STATUS_REASONS
    assert groups["queue_leaf_nodes"][0]["status_reason"] == "waiting_for_dependency"
    assert_live_projection_groups_disjoint(projection)

    queue_ids = {item["node_id"] for item in groups["queue_leaf_nodes"]}
    excluded_ids = {item["node_id"] for item in groups["excluded_nodes"]}
    assert queue_ids.isdisjoint(excluded_ids)


def test_traversal_null_returns_empty_groups() -> None:
    plan = _synthetic_generic_plan()
    plan.traversal = None
    projection = build_planner_debug_projection(plan)

    assert projection["current_node"] is None
    assert projection["next_queued_node"] is None
    assert projection["goals"]["main_goal"] == "Generic Sample Calculation"
    assert all(not projection["groups"][key] for key in projection["groups"])


def test_visited_previous_step_picks_prior_expansion_batch() -> None:
    projection = build_planner_debug_projection(_plan_with_multiple_expansions())
    previous = projection["groups"]["visited_previous_step"]

    assert len(previous) == 1
    assert previous[0]["node_id"] == "PARAM-sample-input"
    assert previous[0]["display_name"] == "PARAM-sample-input"


def test_visited_previous_step_prefers_parameter_resolved_event() -> None:
    plan = _synthetic_generic_plan()
    assert plan.traversal is not None
    plan.traversal.traversal_events = [
        TraversalEvent(
            order=1,
            event_type="parameter_resolved",
            node_id="PARAM-straight-pipe-section",
            message="User input resolved for straight_pipe_section.",
        )
    ]
    projection = build_planner_debug_projection(plan)
    previous = projection["groups"]["visited_previous_step"]

    assert len(previous) == 1
    assert previous[0]["node_id"] == "PARAM-straight-pipe-section"


def test_excluded_event_not_in_queue() -> None:
    projection = build_planner_debug_projection(_plan_with_excluded_event())
    groups = projection["groups"]

    assert any(item["node_id"] == "NODE-excluded" for item in groups["excluded_nodes"])
    assert groups["excluded_nodes"][0]["status_reason"] == "branch_condition_not_satisfied"
    assert not any(item["node_id"] == "NODE-excluded" for item in groups["queue_leaf_nodes"])


def test_equation_awaiting_parameter_gathering_in_queue() -> None:
    projection = build_planner_debug_projection(_plan_with_equation_gathering())
    queue = projection["groups"]["queue_leaf_nodes"]

    equation_rows = [row for row in queue if row["node_id"] == "asme-b313-304-1-2-eq-3a"]
    assert equation_rows
    assert equation_rows[0]["status_reason"] == "waiting_for_upstream_equation"
    assert equation_rows[0]["display_name"] == "asme-b313-304-1-2-eq-3a"


def test_goals_from_required_outputs() -> None:
    projection = build_planner_debug_projection(_synthetic_generic_plan())
    goals = projection["goals"]

    assert goals["main_goal"] == "Generic Sample Calculation"
    assert goals["subgoals"] == ["Sample Output", "Sample Report"]


def test_goals_fallback_to_phases() -> None:
    projection = build_planner_debug_projection(_plan_with_phases_fallback())
    assert projection["goals"]["subgoals"] == ["Gather Inputs", "Run Calculation"]


def test_candidate_queue_reason_ready_for_expansion() -> None:
    plan = _synthetic_generic_plan()
    assert plan.traversal is not None
    plan.traversal.pending_expansion_nodes = []
    plan.traversal.candidate_next_nodes = [
        TraversalCandidateNode(
            node_id="NODE-candidate",
            node_type="paragraph",
            title="Candidate Paragraph",
            reason="Next expansion candidate",
        )
    ]
    projection = build_planner_debug_projection(plan)
    queue = projection["groups"]["queue_leaf_nodes"]

    assert len(queue) == 1
    assert queue[0]["status_reason"] == "ready_for_expansion"


def test_display_name_uses_node_id_for_traceability() -> None:
    projection = build_planner_debug_projection(_synthetic_generic_plan())
    visited = projection["groups"]["visited_previous_step"][0]
    assert visited["display_name"] == "WF-GENERIC"
    assert visited["label"] == "Generic Workflow"


def test_live_groups_dedupe_prefers_higher_priority_slot() -> None:
    plan = _synthetic_generic_plan()
    assert plan.traversal is not None
    plan.traversal.traversal_events = [
        TraversalEvent(
            order=1,
            event_type="parameter_resolved",
            node_id="WF-GENERIC",
            message="Workflow root expanded.",
        )
    ]
    plan.traversal.expanded_nodes.append(
        TraversalExpandedNode(
            node_id="NODE-pending",
            node_type="paragraph",
            expanded_at_order=4,
            title="Pending Paragraph",
        )
    )
    projection = build_planner_debug_projection(plan)
    refs = _live_projection_node_refs(projection)
    slots = {node_id: group for group, node_id in refs}
    assert slots["PARAM-sample-input"] == "current_node"
    assert slots["WF-GENERIC"] == "visited_previous_step"
    assert slots["NODE-pending"] == "queue_leaf_nodes"
    assert "NODE-pending" not in {
        node_id for group, node_id in refs if group == "visited_from_beginning"
    }
    assert_live_projection_groups_disjoint(projection)


def test_planner_debug_projection_for_task_from_synthetic_outputs() -> None:
    manager = TaskStateManager()
    task = manager.create_task("debug-projection-generic", status=TaskStatus.AWAITING_INPUT)
    plan = _synthetic_generic_plan()
    task.outputs["engineering_plan"] = plan.to_dict()

    projection = planner_debug_projection_for_task(task)
    assert projection is not None
    assert projection["current_node"]["node_id"] == "PARAM-sample-input"
    assert projection["goals"]["main_goal"] == "Generic Sample Calculation"
