"""Task-level goal store helpers."""

from __future__ import annotations

from engine.state.execution_context_sync import refresh_execution_context_for_task
from models.goal import Goal
from models.goal_store import GoalStore
from models.task import Task


def _prepare_goal(task: Task, goal: Goal) -> None:
    if goal.provenance.execution_context_id is None:
        goal.provenance.execution_context_id = task.execution_context.id


def store_goal(task: Task, goal: Goal, *, as_root: bool = False) -> Goal:
    _prepare_goal(task, goal)
    task.goal_store.append_goal(goal, as_root=as_root)
    refresh_execution_context_for_task(task)
    return goal


def link_goal_child(task: Task, parent_id: str, child_id: str) -> None:
    task.goal_store.link_child(parent_id, child_id)
    refresh_execution_context_for_task(task)


def expand_goal(task: Task, parent_id: str, child: Goal) -> Goal:
    _prepare_goal(task, child)
    task.goal_store.append_goal(child)
    task.goal_store.link_child(parent_id, child.id)
    refresh_execution_context_for_task(task)
    return child


def active_roots(task: Task) -> list[Goal]:
    return task.goal_store.roots()


def blocked_goals(task: Task) -> list[Goal]:
    return task.goal_store.blocked_goals()


def ready_goals(task: Task) -> list[Goal]:
    return task.goal_store.ready_goals()


def clear_goal_store(task: Task) -> None:
    task.execution_context.goal_store = GoalStore()