"""Planner Layer — navigation intelligence coordinator."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from engine.events.event_logger import EventLogger
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskNotFoundError, TaskStateManager
from models.agent import AgentAction, IntentResult
from models.event import EventType
from models.planning import NavigationPlan, StructuredIntent, WorkflowCandidate
from models.task import Task

from .tools import GraphTools, RuleTools, StateTools

_PIPE_WALL_THICKNESS = "pipe_wall_thickness_design"

_DEFAULT_PRIORITIES: dict[str, list[str]] = {
    _PIPE_WALL_THICKNESS: [
        "material stress evaluation",
        "pressure design / wall thickness",
        "thin-wall applicability check",
    ],
}

_INPUT_QUESTIONS: dict[str, str] = {
    "design_pressure": (
        "To continue the calculation, I need the design pressure because "
        "wall thickness is governed by internal pressure per ASME B31.3 §304.1.1."
    ),
    "outside_diameter": (
        "Please provide the outside diameter of the pipe so the required "
        "wall thickness can be calculated."
    ),
    "material": (
        "I need the pipe material specification to look up allowable stress "
        "at the design temperature."
    ),
    "design_temperature": (
        "Please provide the design temperature because allowable stress "
        "depends on metal temperature."
    ),
}


class Planner:
    """Deterministic navigation layer between intent and graph execution."""

    def __init__(
        self,
        reader: StandardsReader,
        *,
        state: TaskStateManager,
        events: EventLogger | None = None,
    ) -> None:
        self._reader = reader
        self._graph = GraphTools(reader)
        self._state = StateTools(state)
        self._rules = RuleTools(reader)
        self._events = events or EventLogger()

    @property
    def event_logger(self) -> EventLogger:
        return self._events

    def plan(
        self,
        intent: IntentResult,
        task: Task | None,
        *,
        user_message: str | None = None,
    ) -> NavigationPlan:
        structured = self._structured_intent(intent)
        keywords = self._keywords(intent, user_message)
        candidates = self._graph.discover_roots(
            workflow=intent.workflow or intent.intent,
            keywords=keywords,
        )

        if not candidates:
            return NavigationPlan(
                goal=structured.object,
                intent=structured.workflow or structured.action,
                confidence=0.0,
                action=AgentAction.CLARIFY,
                alternative_paths=[
                    "Pipe wall thickness design",
                    "Integrity verification (not yet implemented)",
                    "Pressure test verification (not yet implemented)",
                ],
            )

        selected = self._select_root(candidates, intent)
        if selected is None:
            return NavigationPlan(
                goal=structured.object,
                intent=structured.workflow or structured.action,
                candidate_roots=candidates,
                confidence=max(c.confidence for c in candidates),
                action=AgentAction.CLARIFY,
                alternative_paths=[c.title for c in candidates],
            )

        if not selected.implemented:
            return NavigationPlan(
                goal=structured.object,
                intent=selected.engineering_intent,
                candidate_roots=candidates,
                selected_root=selected.root_id,
                confidence=selected.confidence,
                action=AgentAction.CLARIFY,
                alternative_paths=[c.title for c in candidates if c.implemented],
                questions=[
                    f"The workflow '{selected.title}' is not yet implemented. "
                    "Please choose an available workflow."
                ],
            )

        root_slug = self._graph.normalize_root_id(selected.root_id)
        existing = set(task.inputs.keys()) if task else set()
        missing = self._graph.required_user_inputs(root_slug, existing_inputs=existing)
        questions = [_INPUT_QUESTIONS.get(i, f"Please provide: {i}") for i in missing]

        preview = self._graph.preview_plan(
            task_id=task.task_id if task else "preview",
            root_id=root_slug,
            inputs=task.inputs if task else {},
        )
        exec_nodes = [
            node_id
            for node_id in preview.execution_order
            if str(self._reader.load(node_id).metadata.get("type", "")) != "root"
        ]

        workflow = intent.workflow or intent.intent or selected.engineering_intent
        priorities = _DEFAULT_PRIORITIES.get(
            workflow or "",
            ["dependency resolution", "required input collection"],
        )

        plan = NavigationPlan(
            goal=structured.object or selected.title,
            intent=workflow,
            candidate_roots=candidates,
            selected_root=root_slug,
            selected_nodes=exec_nodes,
            missing_inputs=missing,
            questions=questions,
            confidence=max(structured.confidence, selected.confidence),
            action=AgentAction.REQUEST_INPUT if missing else AgentAction.PROPOSE_PATH,
            priorities=priorities,
        )

        if task is not None:
            try:
                self._state.get_task(task.task_id)
                self._state.persist_planning(
                    task.task_id,
                    workflow=workflow,
                    selected_root=root_slug,
                    active_nodes=exec_nodes,
                    planning_summary=self._summary(plan),
                )
            except TaskNotFoundError:
                pass

        self._events.log(
            EventType.PLANNER_DECISION,
            result={
                "intent": plan.intent,
                "selected_root": plan.selected_root,
                "confidence": plan.confidence,
                "missing_inputs": plan.missing_inputs,
            },
            payload={"candidate_roots": [c.root_id for c in candidates]},
        )

        return plan

    @staticmethod
    def _structured_intent(intent: IntentResult) -> StructuredIntent:
        action = None
        obj = intent.intent
        if intent.intent and "_" in intent.intent:
            parts = intent.intent.split("_", 1)
            action = parts[0]
            obj = intent.intent.replace("_", " ")
        return StructuredIntent(
            action=action,
            object=obj,
            domain=intent.domain,
            confidence=intent.confidence,
            workflow=intent.workflow or intent.intent,
        )

    @staticmethod
    def _keywords(intent: IntentResult, user_message: str | None) -> list[str]:
        tokens: list[str] = []
        if user_message:
            tokens.append(user_message.lower())
        if intent.intent:
            tokens.append(intent.intent.replace("_", " "))
        if intent.domain:
            tokens.append(intent.domain)
        return tokens

    @staticmethod
    def _select_root(
        candidates: list[WorkflowCandidate],
        intent: IntentResult,
    ) -> WorkflowCandidate | None:
        if not candidates:
            return None

        implemented = [c for c in candidates if c.implemented]

        if intent.workflow or intent.intent:
            target = intent.workflow or intent.intent
            for candidate in candidates:
                if candidate.engineering_intent == target:
                    return candidate
                if candidate.root_id == target:
                    return candidate

        if not intent.workflow and not intent.intent and len(candidates) > 1:
            best = candidates[0]
            runner_up = candidates[1]
            if runner_up.confidence > best.confidence - 0.25:
                return None

        high = [c for c in implemented if c.confidence >= 0.85]
        if len(high) == 1:
            return high[0]
        if len(implemented) == 1:
            return implemented[0]
        if len(candidates) == 1:
            return candidates[0]
        return None

    @staticmethod
    def _summary(plan: NavigationPlan) -> dict[str, Any]:
        return {
            "goal": plan.goal,
            "intent": plan.intent,
            "selected_root": plan.selected_root,
            "selected_nodes": plan.selected_nodes,
            "missing_inputs": plan.missing_inputs,
            "confidence": plan.confidence,
            "action": plan.action.value,
        }
