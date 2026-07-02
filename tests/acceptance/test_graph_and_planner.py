"""Acceptance criteria §6 and §7 — graph engine and planner."""

from __future__ import annotations

from engine.graph.graph_engine import GraphEngine
from engine.planner.planner import Planner
from engine.state.goal_projection import planning_projection
from models.agent import AgentAction
from models.agent import IntentResult
from models.task import Task, new_task, TaskStatus
from tests.acceptance.helpers import (
    MATERIAL_STRESS_NODE,
    PIPE_WALL_THICKNESS_ROOT,
    WALL_THICKNESS_NODE,
    pipe_thickness_intent,
    plan_pipe_thickness,
    sample_inputs,
)


class TestGraphEngineAcceptance:
    """§6 Graph Engine Acceptance."""

    def test_discovers_nodes_for_integrity_related_request(self, standards_reader) -> None:
        candidates = GraphEngine().discover_roots(
            standards_reader,
            keywords=["verify pipe integrity"],
        )
        assert candidates
        assert any(candidate.root_id == PIPE_WALL_THICKNESS_ROOT for candidate in candidates)

    def test_dependency_ordering_material_before_thickness(self, standards_reader) -> None:
        plan = GraphEngine().build_plan(
            task_id="acceptance-graph-order",
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs=sample_inputs(),
            reader=standards_reader,
        )
        assert plan.execution_order.index(MATERIAL_STRESS_NODE) < plan.execution_order.index(
            WALL_THICKNESS_NODE
        )

    def test_execution_trace_records_node_and_dependency_context(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        from tests.acceptance.helpers import run_completed_workflow

        task_id = "acceptance-graph-trace"
        run_completed_workflow(state_manager, standards_reader, task_id)
        trace = state_manager.get_task(task_id).outputs["_execution_trace"]

        node_ids = [entry["node_id"] for entry in trace if isinstance(entry, dict)]
        assert MATERIAL_STRESS_NODE in node_ids
        assert WALL_THICKNESS_NODE in node_ids

        thickness_entry = next(entry for entry in trace if entry.get("node_id") == WALL_THICKNESS_NODE)
        assert thickness_entry.get("trace")
        assert thickness_entry.get("inputs") is not None


class TestPlannerAcceptance:
    """§7 Planner Acceptance."""

    def test_identifies_workflow_and_missing_information(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task = state_manager.create_task("acceptance-planner", status=TaskStatus.AWAITING_INPUT)
        plan = plan_pipe_thickness(
            standards_reader,
            state_manager,
            task,
            user_message="Calculate pipe thickness",
        )

        assert plan.selected_root == PIPE_WALL_THICKNESS_ROOT
        assert MATERIAL_STRESS_NODE in plan.selected_nodes
        assert WALL_THICKNESS_NODE not in plan.selected_nodes
        assert (
            "straight_pipe_section" in plan.missing_assumptions
            or "straight_pipe_section" in (plan.phase_missing.get("expansion_assumptions") or [])
        )
        assert (
            "pressure_loading" in plan.missing_assumptions
            or "pressure_loading" in (plan.phase_missing.get("path_decisions") or [])
        )
        assert plan.missing_inputs == []
        assert plan.questions

    def test_generates_task_plan_in_state(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task = state_manager.create_task("acceptance-plan-store", status=TaskStatus.AWAITING_INPUT)
        plan_pipe_thickness(standards_reader, state_manager, task)
        stored = state_manager.get_task(task.task_id)

        assert planning_projection(stored)
        assert stored.active_nodes

    def test_ambiguous_integrity_request_requests_clarification(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        planner = Planner(standards_reader, state=state_manager)
        intent = IntentResult(intent=None, domain="piping", confidence=0.3)
        plan = planner.plan(intent, new_task("ambiguous", status=TaskStatus.ACTIVE), user_message="verify pipe integrity")

        assert plan.action == AgentAction.CLARIFY
        assert plan.alternative_paths

    def test_planner_does_not_execute_calculations(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task = state_manager.create_task("acceptance-planner-no-exec", status=TaskStatus.AWAITING_INPUT)
        for engineering_input in sample_inputs().values():
            state_manager.store_input(task.task_id, engineering_input)
        plan_pipe_thickness(standards_reader, state_manager, task)

        stored = state_manager.get_task(task.task_id)
        assert "required_thickness" not in stored.outputs
        assert "_execution_trace" not in stored.outputs
