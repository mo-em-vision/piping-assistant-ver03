"""Acceptance criteria §8 — AI boundary acceptance."""

from __future__ import annotations

from ai.agents.input_agent import InputAgent
from ai.agents.planner_agent import PlannerAgent
from cli.orchestrator import ChatOrchestrator
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, IntentResult
from models.task import Task, TaskStatus
from tests.agents.conftest import FakeLLMClient


class TestAiBoundaryAcceptance:
    """§8 AI Boundary — agents navigate and explain; they do not decide engineering truth."""

    def test_input_agent_requests_information_without_calculating(self) -> None:
        agent = InputAgent(client=None)
        task = Task(task_id="acceptance-ai-input", status=TaskStatus.AWAITING_INPUT)

        result = agent.analyze(task, workflow=PIPE_WALL_THICKNESS_DESIGN)

        assert result.missing_inputs
        assert result.requests
        assert not hasattr(result, "required_thickness")
        assert all(request.input_id for request in result.requests)

    def test_planner_agent_does_not_return_calculated_values(self) -> None:
        agent = PlannerAgent(client=None)
        intent = IntentResult(
            intent=PIPE_WALL_THICKNESS_DESIGN,
            domain="piping",
            confidence=0.95,
        )

        result = agent.plan(intent)

        assert result.action in {AgentAction.PROPOSE_PATH, AgentAction.REQUEST_INPUT, AgentAction.CLARIFY}
        assert "required_thickness" not in str(result.__dict__)

    def test_orchestrator_does_not_emit_engineering_results_without_execution(self) -> None:
        manager = TaskStateManager()
        orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))
        response, _ = orchestrator.handle_message("Calculate pipe wall thickness")

        assert response.status in {"waiting_input", "clarify", "ready"}
        assert "required_thickness" not in (response.message or "").lower()
        if response.data:
            assert "required_thickness" not in response.data

    def test_agents_decide_next_action_not_engineering_truth(self) -> None:
        """Principle: agents decide what to do next, but never what the truth is."""
        manager = TaskStateManager()
        orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))
        response, debug = orchestrator.handle_message("Calculate pipe wall thickness", debug_ai=True)

        assert response.status == "waiting_input"
        assert "Planner Agent" in debug or response.task_id is not None
        task = manager.get_active_task()
        assert task is not None
        assert "required_thickness" not in task.outputs
