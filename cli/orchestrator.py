"""Wire CLI requests through agents and state manager — no engineering logic."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai.agents.context_agent import ContextAgent
from ai.agents.input_agent import InputAgent
from ai.agents.intent_agent import IntentAgent
from ai.agents.planner_agent import PlannerAgent
from ai.agents._constants import missing_pipe_inputs
from ai.client import MissingAPIKeyError, OpenAIClient
from ai.input_extractor import ExtractionResult, extract_pipe_wall_thickness_inputs
from ai.response.response_handler import ResponseHandler
from engine.reference.standards_reader import StandardsReader
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, AgentContext
from models.task import TaskStatus

from cli.responses import CLIResponse
from cli.session_store import new_task_id


class ChatOrchestrator:
    """Coordinates navigation agents for the chat command."""

    def __init__(
        self,
        state_manager: TaskStateManager,
        *,
        llm_client: Any | None = None,
        standards_root: Path | None = None,
    ) -> None:
        client = llm_client
        if client is None:
            try:
                client = OpenAIClient.from_settings()
            except MissingAPIKeyError:
                client = None

        project_root = Path(__file__).resolve().parents[1]
        reader = StandardsReader(
            standards_root or project_root / "standards",
            standard="asme_b31.3",
        )

        self.state_manager = state_manager
        self.standards_reader = reader
        self.intent_agent = IntentAgent(client=client)
        self.planner_agent = PlannerAgent(client=client, reader=reader, state=state_manager)
        self.input_agent = InputAgent(client=client)
        self.context_agent = ContextAgent(client=client)
        self.response_handler = ResponseHandler()

    def handle_message(
        self,
        message: str,
        *,
        debug_ai: bool = False,
    ) -> tuple[CLIResponse, dict[str, Any]]:
        debug: dict[str, Any] = {}
        active = self.state_manager.get_active_task()
        extraction = ExtractionResult()

        if active and active.status not in {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}:
            extraction = self._extract_and_store_inputs(active.task_id, message)
            active = self.state_manager.get_task(active.task_id)

        workflow = self._resolve_workflow(active)
        missing_inputs = missing_pipe_inputs(active.inputs) if active else []

        context = AgentContext(
            active_task_id=active.task_id if active else None,
            user_message=message,
            workflow=workflow,
            missing_inputs=missing_inputs,
        )

        context_result = self.context_agent.evaluate(message, context=context)
        debug["Context Agent"] = asdict(context_result)
        if context_result.context_switch_detected:
            return (
                CLIResponse(
                    status="context_switch",
                    message=context_result.message,
                    task_id=context.active_task_id if active else None,
                ),
                debug if debug_ai else {},
            )

        intent = self.intent_agent.analyze(message, context=context)
        debug["Intent Agent"] = asdict(intent)

        if intent.action == AgentAction.CLARIFY:
            return (
                CLIResponse(
                    status="clarify",
                    message=intent.message
                    or "Please clarify your engineering request.",
                    data=asdict(intent),
                ),
                debug if debug_ai else {},
            )

        workflow = intent.workflow or intent.intent
        task = active
        if task is None or task.status in {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}:
            task_id = new_task_id(workflow or "task")
            task = self.state_manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
            extraction = self._merge_extraction(
                extraction,
                self._extract_and_store_inputs(task.task_id, message),
            )
            task = self.state_manager.get_task(task.task_id)
        elif task.status == TaskStatus.PAUSED:
            self.state_manager.resume_task(task.task_id)
            task = self.state_manager.get_task(task.task_id)

        navigation_plan = self.planner_agent.plan_navigation(intent, task, user_message=message)
        planner_result = PlannerAgent._to_planner_result(navigation_plan)
        debug["Planner Agent"] = asdict(navigation_plan)

        if navigation_plan.action == AgentAction.CLARIFY:
            options = navigation_plan.alternative_paths or navigation_plan.questions
            message_text = (
                "I found several possible engineering workflows:\n"
                + "\n".join(f"- {item}" for item in options)
                if options
                else "Please clarify which engineering workflow you need."
            )
            return (
                CLIResponse(
                    status="clarify",
                    message=message_text,
                    task_id=task.task_id,
                    data=asdict(navigation_plan),
                ),
                debug if debug_ai else {},
            )

        input_result = self.input_agent.analyze(
            task,
            workflow=workflow,
            context=context,
            navigation_plan=navigation_plan,
        )
        debug["Input Agent"] = asdict(input_result)

        if input_result.missing_inputs:
            self.state_manager.update_task_status(task.task_id, TaskStatus.AWAITING_INPUT)
            formatted = self.response_handler.format_input_requests(
                input_result,
                rejections=extraction.rejected,
            )
            first = input_result.requests[0] if input_result.requests else None
            return (
                CLIResponse(
                    status="waiting_input",
                    message=formatted,
                    question=navigation_plan.questions[0]
                    if navigation_plan.questions
                    else f"Please provide: {', '.join(input_result.missing_inputs)}",
                    required_by=first.node_id if first else None,
                    task_id=task.task_id,
                    data={"missing_inputs": input_result.missing_inputs},
                ),
                debug if debug_ai else {},
            )

        self.state_manager.update_task_status(task.task_id, TaskStatus.ACTIVE)
        summary = self.response_handler.format_intent(intent)
        plan_summary = self.response_handler.format_planner(planner_result)
        return (
            CLIResponse(
                status="ready",
                message=f"{summary}\n\n{plan_summary}",
                task_id=task.task_id,
                data={"workflow": workflow, "selected_root": navigation_plan.selected_root},
            ),
            debug if debug_ai else {},
        )

    @staticmethod
    def _resolve_workflow(active: Any | None) -> str | None:
        if active is None:
            return None
        workflow = active.outputs.get("workflow")
        if workflow:
            return str(workflow)
        return PIPE_WALL_THICKNESS_DESIGN

    def _extract_and_store_inputs(self, task_id: str, message: str) -> ExtractionResult:
        result = extract_pipe_wall_thickness_inputs(message)
        task = self.state_manager.get_task(task_id)
        for inp in result.extracted.values():
            if inp.input_id not in task.inputs:
                self.state_manager.store_input(task_id, inp)
        return result

    @staticmethod
    def _merge_extraction(
        first: ExtractionResult,
        second: ExtractionResult,
    ) -> ExtractionResult:
        merged_extracted = dict(first.extracted)
        merged_extracted.update(second.extracted)
        return ExtractionResult(
            extracted=merged_extracted,
            rejected=first.rejected + second.rejected,
        )
