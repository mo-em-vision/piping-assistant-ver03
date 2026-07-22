"""Missing input identification and explanation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.messaging.parameter_input_prompt import build_parameter_input_prompt
from engine.navigation.task_missing_inputs import missing_inputs_for_task
from engine.reference.parameter_keys import param_node_id_for_input
from models.agent import AgentAction, AgentContext, InputAgentResult, InputRequest
from models.planning import NavigationPhase, NavigationPlan
from models.task import Task

from ai.agents.base import BaseAgent

if TYPE_CHECKING:
    from engine.reference.standards_reader import StandardsReader
    from engine.state.state_manager import TaskStateManager

_DETERMINISTIC_PHASES = frozenset(
    {
        NavigationPhase.EXPANSION_ASSUMPTIONS,
        NavigationPhase.PATH_DECISIONS,
        NavigationPhase.COEFFICIENT_RESOLUTION,
        NavigationPhase.EXECUTION_ASSUMPTIONS,
    }
)


class InputAgent(BaseAgent):
    prompt_file = "input_agent.md"

    def analyze(
        self,
        task: Task,
        *,
        workflow: str | None = None,
        context: AgentContext | None = None,
        navigation_plan: NavigationPlan | None = None,
        reader: StandardsReader | None = None,
    ) -> InputAgentResult:
        missing = self._missing_inputs(task, navigation_plan, reader=reader)
        if not missing:
            return InputAgentResult(missing_inputs=[], action=AgentAction.REQUEST_INPUT)

        requests = [
            self._build_request(task, input_id, navigation_plan, reader=reader)
            for input_id in missing
        ]

        if (
            self._client is not None
            and missing
            and not self._uses_deterministic_prompt(navigation_plan)
        ):
            requests = self._enrich_with_llm(task, missing, requests, context, reader=reader)

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
        navigation_plan: NavigationPlan | None = None,
        reader: StandardsReader | None = None,
    ) -> InputAgentResult:
        task = state_manager.get_task(task_id)
        return self.analyze(
            task,
            workflow=workflow,
            context=context,
            navigation_plan=navigation_plan,
            reader=reader,
        )

    def _missing_inputs(
        self,
        task: Task,
        navigation_plan: NavigationPlan | None,
        *,
        reader: StandardsReader | None,
    ) -> list[str]:
        if navigation_plan:
            phase_fields = navigation_plan.phase_missing.get(
                navigation_plan.current_phase.value,
                [],
            )
            if phase_fields:
                return list(phase_fields)

            missing: list[str] = []
            if navigation_plan.missing_assumptions:
                missing.extend(navigation_plan.missing_assumptions)
            if navigation_plan.missing_inputs:
                for input_id in navigation_plan.missing_inputs:
                    if input_id not in missing:
                        missing.append(input_id)
            if navigation_plan.missing_execution_assumptions:
                for input_id in navigation_plan.missing_execution_assumptions:
                    if input_id not in missing:
                        missing.append(input_id)
            if missing:
                return missing

        return missing_inputs_for_task(task, reader=reader)

    @staticmethod
    def _uses_deterministic_prompt(navigation_plan: NavigationPlan | None) -> bool:
        if navigation_plan is None:
            return False
        return navigation_plan.current_phase in _DETERMINISTIC_PHASES

    def _build_request(
        self,
        task: Task,
        input_id: str,
        navigation_plan: NavigationPlan | None,
        *,
        reader: StandardsReader | None,
    ) -> InputRequest:
        reason = f"Required input: {input_id}"
        if reader is not None:
            prompt = build_parameter_input_prompt(reader, task, input_id)
            if prompt:
                reason = prompt
        if navigation_plan and navigation_plan.questions:
            for question in navigation_plan.questions:
                if input_id.replace("_", " ") in question.lower():
                    reason = question
                    break

        return InputRequest(
            action=AgentAction.REQUEST_INPUT,
            input_id=input_id,
            symbol=None,
            reason=reason,
            node_id=param_node_id_for_input(input_id),
        )

    def _enrich_with_llm(
        self,
        task: Task,
        missing: list[str],
        requests: list[InputRequest],
        context: AgentContext | None,
        *,
        reader: StandardsReader | None,
    ) -> list[InputRequest]:
        payload = self.complete_json(
            (
                f"Task ID: {task.task_id}\n"
                f"Known inputs: {list(task.fact_store.active_facts().keys())}\n"
                f"Missing inputs: {missing}\n"
                f"Context:\n{self.format_context(context.__dict__ if context else None)}"
            ),
        )
        llm_requests = payload.get("requests", [])
        if not llm_requests:
            return requests

        enriched: list[InputRequest] = []
        request_by_id = {request.input_id: request for request in requests}
        for item in llm_requests:
            input_id = str(item.get("input_id", ""))
            original = request_by_id.get(input_id)
            enriched.append(
                InputRequest(
                    action=AgentAction.REQUEST_INPUT,
                    input_id=input_id,
                    symbol=original.symbol if original else item.get("symbol"),
                    reason=str(item.get("reason", "")),
                    node_id=item.get(
                        "node_id",
                        original.node_id if original else param_node_id_for_input(input_id),
                    ),
                )
            )
        return enriched or requests
