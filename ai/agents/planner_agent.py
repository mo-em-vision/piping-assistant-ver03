"""Graph navigation planning from identified intent — delegates to engine.planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.planner.planner import Planner
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, IntentResult, PlannerResult
from models.planning import NavigationPlan
from models.task import Task, TaskStatus

from ai.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    prompt_file = "planner_agent.md"

    def __init__(
        self,
        client: Any | None = None,
        *,
        reader: StandardsReader | None = None,
        state: TaskStateManager | None = None,
    ) -> None:
        super().__init__(client)
        self._reader = reader
        self._state = state

    def plan_navigation(
        self,
        intent: IntentResult,
        task: Task | None = None,
        *,
        user_message: str | None = None,
    ) -> NavigationPlan:
        state = self._state or TaskStateManager()
        reader = self._reader or self._default_reader()

        if task is None:
            task = Task(task_id="planner-preview", status=TaskStatus.ACTIVE)

        planner = Planner(reader, state=state)
        navigation = planner.plan(intent, task, user_message=user_message)

        if navigation.action == AgentAction.CLARIFY and self._client is not None:
            try:
                llm_result = self._plan_with_llm(intent, navigation)
                if llm_result.root_nodes:
                    navigation.selected_root = llm_result.root_nodes[0]
                    navigation.priorities = llm_result.priorities or navigation.priorities
                    navigation.confidence = llm_result.confidence
                    navigation.action = llm_result.action
            except Exception:
                pass

        return navigation

    def plan(
        self,
        intent: IntentResult,
        task: Task | None = None,
        *,
        user_message: str | None = None,
    ) -> PlannerResult:
        navigation = self.plan_navigation(intent, task, user_message=user_message)
        return self._to_planner_result(navigation)

    def _plan_with_llm(
        self,
        intent: IntentResult,
        navigation: NavigationPlan,
    ) -> PlannerResult:
        payload = self.complete_json(
            (
                f"Intent result:\n{self.format_context(intent.__dict__)}\n\n"
                f"Navigation candidates:\n{self.format_context([c.__dict__ for c in navigation.candidate_roots])}"
            ),
        )
        root_nodes = list(payload.get("root_nodes", []))
        if not root_nodes and navigation.selected_root:
            root_nodes = [navigation.selected_root]
        return PlannerResult(
            priorities=list(payload.get("priorities", navigation.priorities)),
            root_nodes=root_nodes,
            confidence=float(payload.get("confidence", navigation.confidence)),
            action=AgentAction(payload.get("action", navigation.action.value)),
        )

    @staticmethod
    def _to_planner_result(navigation: NavigationPlan) -> PlannerResult:
        root = navigation.selected_root
        root_nodes = [root] if root else []
        return PlannerResult(
            priorities=navigation.priorities,
            root_nodes=root_nodes,
            confidence=navigation.confidence,
            action=navigation.action,
        )

    @staticmethod
    def _default_reader() -> StandardsReader:
        root = Path(__file__).resolve().parents[2]
        return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")
