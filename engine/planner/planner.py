"""Planner Layer — navigation intelligence coordinator."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from engine.events.event_logger import EventLogger
from engine.graph.navigation_phases import build_phased_navigation
from engine.graph.assumption_checker import field_value
from engine.graph.parameter_registry import seed_parameter_registry
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskNotFoundError, TaskStateManager
from models.agent import AgentAction, IntentResult
from models.event import EventType
from models.planning import NavigationPhase, NavigationPlan, StructuredIntent, WorkflowCandidate
from models.task import Task

from .tools import GraphTools, RuleTools, StateTools

_PIPE_WALL_THICKNESS = "pipe_wall_thickness_design"

_DEFAULT_PRIORITIES: dict[str, list[str]] = {
    _PIPE_WALL_THICKNESS: [
        "pressure loading case",
        "material stress evaluation",
        "pressure design / wall thickness",
        "thin-wall applicability check",
    ],
}

_INPUT_QUESTIONS: dict[str, str] = {
    "straight_pipe_section": (
        "Is the pipe wall thickness you would like to calculate for a straight section of pipe? "
        "Non-straight sections (fittings, bends) are not yet supported."
    ),
    "pressure_loading": (
        "Is the pipe subjected to internal or external pressure? "
        "Internal pressure design uses §304.1.2; external pressure design uses §304.1.3."
    ),
    "design_pressure": (
        "To continue the calculation, I need the design pressure because "
        "wall thickness is governed by internal pressure per ASME B31.3 §304.1.2."
    ),
    "outside_diameter": (
        "Please provide the outside diameter of the pipe (mm or in) so the required "
        "wall thickness can be calculated."
    ),
    "nominal_pipe_size": (
        "Please provide the nominal pipe size (NPS) so outside diameter D can be "
        "looked up per ASME B36.10."
    ),
    "d_input_mode": (
        "Provide outside diameter D by nominal pipe size (NPS, looked up per ASME B36.10) "
        "or enter the outside diameter directly (mm or in)?"
    ),
    "corrosion_allowance": (
        "For c (mechanical allowances): the default is 0.5 mm when machined surfaces "
        "or grooves where tolerance is not specified. Confirm or enter another value."
    ),
    "material": (
        "I need the pipe material specification to look up allowable stress "
        "at the design temperature."
    ),
    "design_temperature": (
        "Please provide the design temperature because allowable stress "
        "depends on metal temperature."
    ),
    "external_design_pressure": (
        "Please provide the external design pressure for external pressure "
        "wall thickness design per ASME B31.3 §304.1.3."
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
    "joint_category": (
        "Confirm the pipe/joint category for quality factor E lookup (Tables A-1A and A-1B). "
        "Default is seamless pipe."
    ),
}

_THICKNESS_NODES = ("B313-304.1.2", "B313-304.1.3")


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
        existing_inputs = dict(task.inputs) if task else {}

        if task is not None:
            proposed = self._graph.resolve_and_propose_path_inputs(
                root_slug,
                existing_inputs=existing_inputs,
            )
            if proposed:
                self._state.persist_proposed_inputs(task.task_id, proposed)
                existing_inputs = dict(self._state.get_task(task.task_id).inputs)

        existing_ids = set(existing_inputs.keys())

        preview = self._graph.preview_plan(
            task_id=task.task_id if task else "preview",
            root_id=root_slug,
            inputs=existing_inputs,
        )

        if task is not None and self._graph.expansion_gate_ready(
            root_slug, existing_inputs=existing_inputs
        ):
            registry = self._graph.seed_parameter_registry(
                root_slug,
                existing_inputs=existing_inputs,
            )
            if registry:
                self._state.persist_parameter_registry(task.task_id, registry)
        exec_nodes = [
            node_id
            for node_id in preview.execution_order
            if str(self._reader.load(node_id).metadata.get("type", "")) != "root"
        ]

        assumption_eval = self._graph.evaluate_assumptions(
            root_slug,
            existing_inputs=existing_inputs,
        )
        missing_assumptions = list(assumption_eval.missing_fields)
        assumption_questions = [
            assumption_eval.field_questions.get(field_id, f"Please confirm: {field_id}")
            for field_id in missing_assumptions
        ]

        expansion_eval = self._graph.evaluate_expansion_interactions(
            root_slug,
            existing_inputs=existing_inputs,
        )
        missing_expansion = list(expansion_eval.missing_fields)
        expansion_questions = [
            expansion_eval.field_questions.get(field_id, f"Please confirm: {field_id}")
            for field_id in missing_expansion
        ]

        missing = self._graph.required_user_inputs(
            root_slug,
            existing_inputs=existing_ids,
            task_inputs=existing_inputs,
        )
        input_questions = [_INPUT_QUESTIONS.get(i, f"Please provide: {i}") for i in missing]

        execution_eval = self._graph.evaluate_execution_assumptions(
            root_slug,
            existing_inputs=existing_inputs,
        )
        missing_execution = [
            field_id
            for field_id in execution_eval.missing_fields
            if field_id not in missing_expansion
        ]
        execution_questions = [
            execution_eval.field_questions.get(
                field_id,
                _INPUT_QUESTIONS.get(field_id, f"Please confirm: {field_id}"),
            )
            for field_id in missing_execution
        ]

        exec_nodes = self._graph.expansion_ready_nodes(
            exec_nodes,
            existing_inputs=existing_inputs,
        )

        question_map: dict[str, str] = dict(_INPUT_QUESTIONS)
        for field_id, question in assumption_eval.field_questions.items():
            question_map.setdefault(field_id, question)
        for field_id, question in expansion_eval.field_questions.items():
            question_map.setdefault(field_id, question)
        for field_id, question in execution_eval.field_questions.items():
            question_map.setdefault(field_id, question)

        phased = build_phased_navigation(
            assumption_eval=assumption_eval,
            expansion_eval=expansion_eval,
            user_inputs=missing,
            execution_eval=execution_eval,
            question_map=question_map,
        )

        all_missing = phased.all_missing
        questions = phased.questions

        workflow = intent.workflow or intent.intent or selected.engineering_intent
        priorities = _DEFAULT_PRIORITIES.get(
            workflow or "",
            ["dependency resolution", "required input collection"],
        )
        path_decision = self._path_decision(existing_inputs, exec_nodes)

        plan = NavigationPlan(
            goal=structured.object or selected.title,
            intent=workflow,
            candidate_roots=candidates,
            selected_root=root_slug,
            selected_nodes=exec_nodes,
            missing_assumptions=missing_assumptions,
            missing_execution_assumptions=missing_expansion + missing_execution,
            missing_inputs=missing,
            questions=questions,
            path_decision=path_decision,
            confidence=max(structured.confidence, selected.confidence),
            action=AgentAction.CLARIFY
            if phased.blocked_nodes
            else (AgentAction.REQUEST_INPUT if all_missing else AgentAction.PROPOSE_PATH),
            priorities=priorities,
            current_phase=phased.current_phase,
            phase_missing=phased.phase_missing,
            blocked_nodes=phased.blocked_nodes,
            block_messages=phased.block_messages,
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
                "missing_assumptions": plan.missing_assumptions,
                "missing_execution_assumptions": plan.missing_execution_assumptions,
                "missing_inputs": plan.missing_inputs,
                "path_decision": plan.path_decision,
            },
            payload={"candidate_roots": [c.root_id for c in candidates]},
        )

        return plan

    @staticmethod
    def _path_decision(
        inputs: dict[str, Any],
        exec_nodes: list[str],
    ) -> dict[str, str] | None:
        loading = field_value("pressure_loading", inputs)
        if not loading:
            return None
        thickness_node = next((node for node in exec_nodes if node in _THICKNESS_NODES), None)
        if thickness_node is None:
            return None
        return {
            "field": "pressure_loading",
            "value": loading,
            "selected_node": thickness_node,
        }

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
            "missing_assumptions": plan.missing_assumptions,
            "missing_execution_assumptions": plan.missing_execution_assumptions,
            "missing_inputs": plan.missing_inputs,
            "path_decision": plan.path_decision,
            "confidence": plan.confidence,
            "action": plan.action.value,
        }
