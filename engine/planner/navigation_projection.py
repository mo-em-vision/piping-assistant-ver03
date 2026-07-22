"""Project legacy NavigationPlan views from canonical EngineeringPlan."""

from __future__ import annotations

from typing import Any

from engine.messaging.parameter_input_prompt import build_parameter_input_prompt
from engine.planner.graph_navigation import build_graph_navigation_from_plan
from engine.reference.standards_reader import StandardsReader
from models.agent import AgentAction
from models.engineering_plan import EngineeringPlan
from models.planning import NavigationPhase, NavigationPlan, WorkflowCandidate
from models.task import Task

_PHASE_ORDER = (
    NavigationPhase.EXPANSION_ASSUMPTIONS.value,
    NavigationPhase.PATH_DECISIONS.value,
    NavigationPhase.PARAMETER_GATHERING.value,
    NavigationPhase.COEFFICIENT_RESOLUTION.value,
    NavigationPhase.EXECUTION_ASSUMPTIONS.value,
    NavigationPhase.DEFINITION_EQUATION_COMPLETION.value,
)


def _unique_stable(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _questions_for_phase_missing(
    reader: StandardsReader,
    task: Task,
    phase_missing: dict[str, list[str]],
) -> list[str]:
    questions: list[str] = []
    seen_fields: set[str] = set()
    for phase in _PHASE_ORDER:
        for field in phase_missing.get(phase) or []:
            field_id = str(field).strip()
            if not field_id or field_id in seen_fields:
                continue
            seen_fields.add(field_id)
            prompt = build_parameter_input_prompt(reader, task, field_id)
            if prompt:
                questions.append(prompt)
    return questions


def navigation_plan_from_engineering_plan(
    plan: EngineeringPlan,
    *,
    task: Task | None = None,
    reader: StandardsReader | None = None,
    candidates: list[WorkflowCandidate] | None = None,
    confidence: float = 0.0,
    intent: str | None = None,
    goal: str | None = None,
    path_decision: dict[str, str] | None = None,
    blocked_nodes: list[str] | None = None,
    block_messages: list[str] | None = None,
) -> NavigationPlan:
    """Build a read-only NavigationPlan projection from a stored EngineeringPlan."""
    nav = build_graph_navigation_from_plan(plan)
    phase_missing = {
        str(phase): list(fields or [])
        for phase, fields in (nav.get("phase_missing") or {}).items()
        if isinstance(fields, list)
    }

    try:
        current_phase = NavigationPhase(
            str(nav.get("current_phase") or NavigationPhase.READY.value)
        )
    except ValueError:
        current_phase = NavigationPhase.READY

    missing_assumptions = _unique_stable(
        [str(item) for item in (nav.get("missing_expansion_assumptions") or []) if item]
        + [str(item) for item in (nav.get("missing_path_decisions") or []) if item]
    )
    missing_execution = [
        str(item) for item in (nav.get("missing_execution_assumptions") or []) if item
    ]
    missing_inputs = _unique_stable(
        [
            str(field)
            for fields in phase_missing.values()
            for field in fields
            if str(field).strip()
        ]
    )

    selected_nodes: list[str] = []
    if plan.graph and plan.graph.selected_subgraph_node_ids:
        selected_nodes = [str(node_id) for node_id in plan.graph.selected_subgraph_node_ids if node_id]
    elif task is not None:
        selected_nodes = [str(node_id) for node_id in (task.outputs.get("selected_nodes") or []) if node_id]

    resolved_path_decision = path_decision
    if resolved_path_decision is None and task is not None:
        stored = task.outputs.get("path_decision")
        if isinstance(stored, dict):
            resolved_path_decision = stored

    questions: list[str] = []
    if reader is not None and task is not None:
        questions = _questions_for_phase_missing(reader, task, phase_missing)

    blocked = list(blocked_nodes or [])
    has_missing = bool(missing_assumptions or missing_execution or missing_inputs)
    if blocked:
        action = AgentAction.CLARIFY
    elif has_missing:
        action = AgentAction.REQUEST_INPUT
    else:
        action = AgentAction.PROPOSE_PATH

    root_title = plan.root_goal.title if plan.root_goal else None
    return NavigationPlan(
        goal=goal or root_title,
        intent=intent or plan.workflow_id,
        candidate_roots=list(candidates or []),
        selected_root=plan.workflow_id,
        selected_nodes=selected_nodes,
        missing_assumptions=missing_assumptions,
        missing_execution_assumptions=missing_execution,
        missing_inputs=missing_inputs,
        questions=questions,
        path_decision=resolved_path_decision,
        confidence=confidence,
        action=action,
        priorities=["dependency resolution", "required input collection"],
        current_phase=current_phase,
        phase_missing=phase_missing,
        blocked_nodes=blocked,
        block_messages=list(block_messages or []),
    )


def navigation_plan_from_task(
    task: Task,
    reader: StandardsReader,
    *,
    candidates: list[WorkflowCandidate] | None = None,
    confidence: float = 0.0,
    intent: str | None = None,
    goal: str | None = None,
) -> NavigationPlan | None:
    """Return a NavigationPlan projection when the task has a stored EngineeringPlan."""
    from engine.planner.plan_selection import engineering_plan_for_task

    plan = engineering_plan_for_task(task)
    if plan is None:
        return None

    path_decision = task.outputs.get("path_decision")
    return navigation_plan_from_engineering_plan(
        plan,
        task=task,
        reader=reader,
        candidates=candidates,
        confidence=confidence,
        intent=intent,
        goal=goal,
        path_decision=path_decision if isinstance(path_decision, dict) else None,
    )
