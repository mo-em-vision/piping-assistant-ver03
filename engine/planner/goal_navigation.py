"""Goal-guided navigation: pick the next user-facing ask from the runtime goal tree."""

from __future__ import annotations

from typing import Any

from models.fact import fact_is_expansion_ready
from models.goal import Goal, GoalClass, SatisfactionStatus, goal_parameter_key
from models.task import Task

_USER_ASK_GOAL_CLASSES = frozenset({GoalClass.INPUT, GoalClass.SELECTION})


def _param_satisfied(task: Task, parameter: str) -> bool:
    fact = task.fact_store.active_fact(parameter)
    if fact is None:
        return False
    return fact_is_expansion_ready(fact)


def _sorted_child_goals(task: Task, root: Goal) -> list[Goal]:
    store = task.goal_store
    children = store.children(root.id)
    graph_order = task.outputs.get("graph_input_order")
    order_index: dict[str, int] = {}
    if isinstance(graph_order, list):
        order_index = {str(item): index for index, item in enumerate(graph_order)}

    def sort_key(goal: Goal) -> tuple[int, int, str]:
        meta_order = goal.metadata.get("order")
        meta = int(meta_order) if isinstance(meta_order, int) else 10_000
        param = goal_parameter_key(goal)
        graph = order_index.get(param, 10_000)
        return (graph, meta, goal.key)

    return sorted(children, key=sort_key)


def next_actionable_goal(task: Task) -> Goal | None:
    """First unsatisfied input/selection goal that is ready for user submission."""
    roots = task.goal_store.roots()
    if not roots:
        return None

    root = roots[0]
    for goal in _sorted_child_goals(task, root):
        if goal.goal_class not in _USER_ASK_GOAL_CLASSES:
            continue
        if goal.satisfaction.status in {
            SatisfactionStatus.SATISFIED,
            SatisfactionStatus.SUPERSEDED,
        }:
            continue
        if goal.state.blocked_by:
            continue
        if goal.satisfaction.status == SatisfactionStatus.BLOCKED:
            continue
        param = goal_parameter_key(goal)
        if _param_satisfied(task, param):
            continue
        if goal.satisfaction.status in {SatisfactionStatus.PENDING, SatisfactionStatus.READY}:
            return goal
    return None


def clarify_blocked_goal(task: Task) -> Goal | None:
    """First blocked goal with a user-facing clarify prompt when no input is actionable."""
    if next_actionable_goal(task) is not None:
        return None
    for goal in task.goal_store.blocked_goals():
        if goal.question and goal.question.prompt.strip():
            return goal
    return None


def goal_guided_parameter_ids(task: Task) -> list[str]:
    """Parameter ids the user should submit next (one primary ask)."""
    goal = next_actionable_goal(task)
    if goal is None:
        return []
    return [goal_parameter_key(goal)]


def _prompt_for_goal(goal: Goal, planning: dict[str, Any]) -> str | None:
    if goal.question and goal.question.prompt.strip():
        return goal.question.prompt.strip()
    phase_questions = planning.get("phase_questions") or {}
    phase_missing = planning.get("phase_missing") or {}
    param = goal_parameter_key(goal)
    if not isinstance(phase_questions, dict) or not isinstance(phase_missing, dict):
        return None
    for phase, fields in phase_missing.items():
        if not isinstance(fields, list) or param not in fields:
            continue
        questions = phase_questions.get(phase)
        if isinstance(questions, dict):
            prompt = questions.get(param)
            if isinstance(prompt, str) and prompt.strip():
                return prompt.strip()
        elif isinstance(questions, list):
            index = fields.index(param)
            if index < len(questions):
                prompt = questions[index]
                if isinstance(prompt, str) and prompt.strip():
                    return prompt.strip()
    return None


def build_current_ask(task: Task, planning: dict[str, Any]) -> dict[str, Any] | None:
    """API-facing current ask for the desktop workflow composer."""
    goal = next_actionable_goal(task)
    if goal is not None:
        param = goal_parameter_key(goal)
        return {
            "kind": "input",
            "parameter_id": param,
            "prompt": _prompt_for_goal(goal, planning),
        }

    blocked = clarify_blocked_goal(task)
    if blocked is not None:
        prompt = blocked.question.prompt.strip() if blocked.question else "Workflow path is blocked."
        return {
            "kind": "clarify",
            "parameter_id": None,
            "prompt": prompt,
        }

    from api.workflow_timeline import submittable_parameter_ids

    submittable = submittable_parameter_ids(task, planning)
    if submittable:
        param = submittable[0]
        phase_questions = planning.get("phase_questions") or {}
        phase_missing = planning.get("phase_missing") or {}
        prompt: str | None = None
        if isinstance(phase_questions, dict) and isinstance(phase_missing, dict):
            for phase, fields in phase_missing.items():
                if not isinstance(fields, list) or param not in fields:
                    continue
                questions = phase_questions.get(phase)
                if isinstance(questions, dict):
                    candidate = questions.get(param)
                    if isinstance(candidate, str) and candidate.strip():
                        prompt = candidate.strip()
                        break
        return {
            "kind": "input",
            "parameter_id": param,
            "prompt": prompt,
        }

    current_phase = str(planning.get("current_phase") or "")
    if current_phase == "ready":
        return None

    phase_missing = planning.get("phase_missing") or {}
    if isinstance(phase_missing, dict):
        for fields in phase_missing.values():
            if isinstance(fields, list) and fields:
                return {
                    "kind": "waiting",
                    "parameter_id": None,
                    "prompt": None,
                }

    return None
