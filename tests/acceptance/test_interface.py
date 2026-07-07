"""Acceptance criteria §3 and §21 — chat interaction and user visibility."""

from __future__ import annotations

from api.chat_orchestrator import ChatOrchestrator
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import plan_pipe_thickness
from tests.agents.conftest import FakeLLMClient


class TestSupportedInterface:
    """§3 Supported Interface — desktop chat interaction."""

    def test_chat_starts_task_and_requests_inputs(self) -> None:
        manager = TaskStateManager()
        orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))
        response, _ = orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")

        assert response.status == "waiting_input"
        assert response.task_id is not None
        assert response.question


class TestUserVisibility:
    """§21 User Visibility — selected nodes, dependencies, and execution path."""

    def test_planner_exposes_selected_nodes_and_missing_inputs(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task = state_manager.create_task("acceptance-visibility", status=TaskStatus.AWAITING_INPUT)
        plan = plan_pipe_thickness(standards_reader, state_manager, task)

        assert plan.selected_nodes
        assert plan.missing_assumptions or plan.phase_missing.get("expansion_assumptions")
        assert plan.questions
        assert any(
            "straight" in question.lower()
            or "pressure" in question.lower()
            or "304.1.1" in question
            for question in plan.questions
        )
