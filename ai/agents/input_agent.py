"""Missing input identification and explanation."""

from __future__ import annotations

from typing import Any

from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, AgentContext, InputAgentResult, InputRequest
from models.task import Task

from ai.agents._constants import (
    PIPE_WALL_THICKNESS_DESIGN,
    PIPE_WALL_THICKNESS_NODE,
    REQUIRED_DEPENDENCY_INPUTS,
    REQUIRED_USER_INPUTS,
)
from ai.agents.base import BaseAgent


class InputAgent(BaseAgent):
    prompt_file = "input_agent.md"

    _REASONS: dict[str, str] = {
        "design_pressure": "Required by ASME B31.3 §304.1.1 for thickness calculation.",
        "outside_diameter": "Required by ASME B31.3 §304.1.1 for thickness calculation.",
        "allowable_stress": "Required by ASME B31.3 §304.1.1; sourced from material stress evaluation.",
    }

    _SYMBOLS: dict[str, str] = {
        "design_pressure": "P",
        "outside_diameter": "D",
        "allowable_stress": "S",
    }

    def analyze(
        self,
        task: Task,
        *,
        workflow: str | None = None,
        context: AgentContext | None = None,
    ) -> InputAgentResult:
        missing = self._missing_for_workflow(task, workflow)
        if not missing:
            return InputAgentResult(missing_inputs=[], action=AgentAction.REQUEST_INPUT)

        requests = [self._build_request(input_id) for input_id in missing]

        if self._client is not None and missing:
            requests = self._enrich_with_llm(task, missing, requests, context)

        return InputAgentResult(
            requests=requests,
            missing_inputs=missing,
            action=AgentAction.REQUEST_INPUT,
        )

    def analyze_from_state(
        self,
        state_manager: TaskStateManager,
        task_id: str,
        *,
        workflow: str | None = None,
        context: AgentContext | None = None,
    ) -> InputAgentResult:
        task = state_manager.get_task(task_id)
        return self.analyze(task, workflow=workflow, context=context)

    def _missing_for_workflow(self, task: Task, workflow: str | None) -> list[str]:
        if workflow != PIPE_WALL_THICKNESS_DESIGN and workflow is not None:
            return []

        required = list(REQUIRED_USER_INPUTS) + list(REQUIRED_DEPENDENCY_INPUTS)
        return [input_id for input_id in required if input_id not in task.inputs]

    def _build_request(self, input_id: str) -> InputRequest:
        return InputRequest(
            action=AgentAction.REQUEST_INPUT,
            input_id=input_id,
            symbol=self._SYMBOLS.get(input_id),
            reason=self._REASONS.get(input_id, f"Required input: {input_id}"),
            node_id=PIPE_WALL_THICKNESS_NODE,
        )

    def _enrich_with_llm(
        self,
        task: Task,
        missing: list[str],
        requests: list[InputRequest],
        context: AgentContext | None,
    ) -> list[InputRequest]:
        payload = self.complete_json(
            (
                f"Task ID: {task.task_id}\n"
                f"Known inputs: {list(task.inputs.keys())}\n"
                f"Missing inputs: {missing}\n"
                f"Context:\n{self.format_context(context.__dict__ if context else None)}"
            ),
        )
        llm_requests = payload.get("requests", [])
        if not llm_requests:
            return requests

        enriched: list[InputRequest] = []
        for item in llm_requests:
            enriched.append(
                InputRequest(
                    action=AgentAction.REQUEST_INPUT,
                    input_id=str(item.get("input_id", "")),
                    symbol=item.get("symbol"),
                    reason=str(item.get("reason", "")),
                    node_id=item.get("node_id", PIPE_WALL_THICKNESS_NODE),
                )
            )
        return enriched or requests
