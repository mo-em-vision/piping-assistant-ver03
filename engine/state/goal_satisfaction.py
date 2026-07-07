"""Recompute goal satisfaction from active Facts."""

from __future__ import annotations

from models.fact import fact_is_expansion_ready
from models.goal import (
    Goal,
    GoalClass,
    GoalRuntimeStatus,
    SatisfactionStatus,
    goal_parameter_key,
)
from models.goal_store import GoalStore
from models.task import Task


def _param_key_from_ref(parameter: str) -> str:
    if parameter.startswith("PARAM-"):
        return parameter[len("PARAM-") :].replace("-", "_")
    return parameter


def _fact_satisfies_parameter(task: Task, parameter: str) -> str | None:
    key = _param_key_from_ref(parameter)
    fact = task.fact_store.active_fact(key)
    if fact is None:
        return None
    if not fact_is_expansion_ready(fact):
        return None
    return fact.id


def _required_facts_satisfied(task: Task, goal: Goal) -> tuple[bool, list[str]]:
    blocked: list[str] = []
    for ref in goal.required_facts:
        fact_id = _fact_satisfies_parameter(task, ref.parameter)
        if fact_id is None:
            blocked.append(_param_key_from_ref(ref.parameter))
    return (len(blocked) == 0, blocked)


def _refresh_goal_node(task: Task, goal: Goal, store: GoalStore) -> None:
    children = store.children(goal.id)
    child_blocked: list[str] = []

    for child in children:
        if child.satisfaction.status not in {
            SatisfactionStatus.SATISFIED,
            SatisfactionStatus.SUPERSEDED,
        }:
            child_blocked.append(child.key)

    req_ok, req_blocked = _required_facts_satisfied(task, goal)
    output_param = (
        goal.satisfaction.required_output.parameter
        if goal.satisfaction.required_output
        else goal.target_parameter
    )
    satisfied_by = _fact_satisfies_parameter(task, output_param)

    if satisfied_by:
        goal.satisfaction.status = SatisfactionStatus.SATISFIED
        goal.satisfaction.satisfied_by = satisfied_by
        goal.state.status = GoalRuntimeStatus.SATISFIED
        goal.state.blocked_by = []
        return

    if child_blocked:
        goal.satisfaction.status = SatisfactionStatus.BLOCKED
        goal.state.status = GoalRuntimeStatus.BLOCKED
        goal.state.blocked_by = list(child_blocked)
        goal.satisfaction.satisfied_by = None
        return

    if not req_ok:
        goal.satisfaction.status = SatisfactionStatus.BLOCKED
        goal.state.status = GoalRuntimeStatus.BLOCKED
        goal.state.blocked_by = list(req_blocked)
        goal.satisfaction.satisfied_by = None
        return

    from engine.graph.definition_equations import has_execution_trace
    from models.planning import NavigationPhase

    if (
        goal.goal_class in {GoalClass.INPUT, GoalClass.SELECTION}
        and str(goal.metadata.get("phase") or "") == NavigationPhase.DEFINITION_EQUATION_COMPLETION.value
        and has_execution_trace(task)
        and task.outputs.get("t") is None
        and task.outputs.get("required_thickness") is None
    ):
        goal.satisfaction.status = SatisfactionStatus.BLOCKED
        goal.state.status = GoalRuntimeStatus.BLOCKED
        goal.state.blocked_by = ["required_thickness"]
        goal.satisfaction.satisfied_by = None
        return

    if goal.goal_class in {
        GoalClass.INPUT,
        GoalClass.SELECTION,
        GoalClass.LOOKUP,
        GoalClass.CALCULATION,
        GoalClass.VALIDATION,
    }:
        goal.satisfaction.status = SatisfactionStatus.READY
        goal.state.status = GoalRuntimeStatus.READY
        goal.state.blocked_by = []
        goal.satisfaction.satisfied_by = None
        return

    goal.satisfaction.status = SatisfactionStatus.PENDING
    goal.state.status = GoalRuntimeStatus.ACTIVE
    goal.state.blocked_by = []
    goal.satisfaction.satisfied_by = None


def refresh_goal_satisfaction(task: Task) -> None:
    """Walk goal tree bottom-up and update blocked_by / satisfaction from facts."""
    store = task.goal_store
    if not store.goals:
        return

    visited: set[str] = set()

    def visit(goal_id: str) -> None:
        if goal_id in visited:
            return
        goal = store.get(goal_id)
        if goal is None:
            return
        for child_id in goal.state.child_goals:
            visit(child_id)
        _refresh_goal_node(task, goal, store)
        visited.add(goal_id)

    for root in store.roots():
        visit(root.id)

    for goal_id in store.goals:
        if goal_id not in visited:
            visit(goal_id)
