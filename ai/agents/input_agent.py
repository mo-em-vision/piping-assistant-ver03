"""Missing input identification and explanation."""

from __future__ import annotations

from typing import Any

from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, AgentContext, InputAgentResult, InputRequest
from models.planning import NavigationPlan
from models.task import Task

from ai.agents._constants import (
    PIPE_WALL_THICKNESS_DESIGN,
    PIPE_WALL_THICKNESS_NODE,
    REQUIRED_ASSUMPTION_FIELDS,
    REQUIRED_LOOKUP_INPUTS,
    REQUIRED_USER_INPUTS,
)
from ai.agents.base import BaseAgent

MATERIAL_STRESS_NODE = "B313-material-stress"


class InputAgent(BaseAgent):
    prompt_file = "input_agent.md"

    _REASONS: dict[str, str] = {
        "straight_pipe_section": (
            "Required before expanding the §304.1.1 wall thickness path. "
            "This workflow currently supports straight pipe sections only."
        ),
        "pressure_loading": (
            "Required before expanding the §304.1.1 wall thickness path. "
            "The equation t = PD/2(SEW+PY) applies only to internally "
            "pressurized pipe."
        ),
        "design_pressure": "Required by ASME B31.3 §304.1.1 for thickness calculation.",
        "outside_diameter": "Required by ASME B31.3 §304.1.1 for thickness calculation.",
        "material": (
            "Required to look up allowable stress at design temperature "
            "from the material stress table."
        ),
        "design_temperature": (
            "Required because allowable stress depends on design metal temperature."
        ),
        "external_design_pressure": (
            "Required for external pressure wall thickness design per ASME B31.3 §304.1.3."
        ),
        "weld_joint_efficiency": (
            "Please confirm the weld joint quality factor E = 1.0 "
            "(default for seamless pipe), or provide a different value."
        ),
        "weld_strength_reduction": (
            "Please confirm the weld strength reduction factor W = 1.0, "
            "or provide a different value."
        ),
        "temperature_coefficient": (
            "Please confirm the temperature coefficient Y = 0.4, "
            "or provide a different value."
        ),
    }

    _SYMBOLS: dict[str, str] = {
        "straight_pipe_section": "straight_pipe_section",
        "pressure_loading": "pressure_loading",
        "design_pressure": "P",
        "outside_diameter": "D",
        "material": "material",
        "design_temperature": "T",
        "external_design_pressure": "P_ext",
        "weld_joint_efficiency": "E",
        "weld_strength_reduction": "W",
        "temperature_coefficient": "Y",
    }

    _NODE_IDS: dict[str, str] = {
        "straight_pipe_section": PIPE_WALL_THICKNESS_NODE,
        "pressure_loading": PIPE_WALL_THICKNESS_NODE,
        "design_pressure": PIPE_WALL_THICKNESS_NODE,
        "outside_diameter": PIPE_WALL_THICKNESS_NODE,
        "external_design_pressure": "B313-304.1.3",
        "weld_joint_efficiency": PIPE_WALL_THICKNESS_NODE,
        "weld_strength_reduction": PIPE_WALL_THICKNESS_NODE,
        "temperature_coefficient": PIPE_WALL_THICKNESS_NODE,
        "material": MATERIAL_STRESS_NODE,
        "design_temperature": MATERIAL_STRESS_NODE,
    }

    def analyze(
        self,
        task: Task,
        *,
        workflow: str | None = None,
        context: AgentContext | None = None,
        navigation_plan: NavigationPlan | None = None,
    ) -> InputAgentResult:
        missing = self._missing_inputs(task, workflow, navigation_plan)
        if not missing:
            return InputAgentResult(missing_inputs=[], action=AgentAction.REQUEST_INPUT)

        requests = [self._build_request(input_id, navigation_plan) for input_id in missing]

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
        navigation_plan: NavigationPlan | None = None,
    ) -> InputAgentResult:
        task = state_manager.get_task(task_id)
        return self.analyze(
            task,
            workflow=workflow,
            context=context,
            navigation_plan=navigation_plan,
        )

    def _missing_inputs(
        self,
        task: Task,
        workflow: str | None,
        navigation_plan: NavigationPlan | None,
    ) -> list[str]:
        if navigation_plan:
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

        if workflow != PIPE_WALL_THICKNESS_DESIGN and workflow is not None:
            return []

        required = list(REQUIRED_USER_INPUTS) + list(REQUIRED_LOOKUP_INPUTS)
        assumption_fields = list(REQUIRED_ASSUMPTION_FIELDS)
        return [
            input_id
            for input_id in assumption_fields + required
            if input_id not in task.inputs
        ]

    def _build_request(
        self,
        input_id: str,
        navigation_plan: NavigationPlan | None,
    ) -> InputRequest:
        reason = self._REASONS.get(input_id, f"Required input: {input_id}")
        if navigation_plan and navigation_plan.questions:
            for question in navigation_plan.questions:
                if input_id.replace("_", " ") in question.lower():
                    reason = question
                    break

        return InputRequest(
            action=AgentAction.REQUEST_INPUT,
            input_id=input_id,
            symbol=self._SYMBOLS.get(input_id),
            reason=reason,
            node_id=self._NODE_IDS.get(input_id, PIPE_WALL_THICKNESS_NODE),
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
        request_by_id = {request.input_id: request for request in requests}
        for item in llm_requests:
            input_id = str(item.get("input_id", ""))
            original = request_by_id.get(input_id)
            enriched.append(
                InputRequest(
                    action=AgentAction.REQUEST_INPUT,
                    input_id=input_id,
                    symbol=(
                        self._SYMBOLS.get(input_id)
                        or (original.symbol if original else None)
                        or item.get("symbol")
                    ),
                    reason=str(item.get("reason", "")),
                    node_id=item.get(
                        "node_id",
                        self._NODE_IDS.get(input_id, PIPE_WALL_THICKNESS_NODE),
                    ),
                )
            )
        return enriched or requests
