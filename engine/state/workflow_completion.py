"""Workflow completion helpers derived from goal_expansion metadata."""

from __future__ import annotations

from engine.planner.workflow_goal_metadata import RootGoalCompletionSpec, RootGoalSpec
from engine.reference.workflow_sidecar import _param_to_field
from models.fact import fact_is_expansion_ready
from models.goal import SatisfactionStatus
from models.task import Task, TaskStatus


def workflow_target_satisfied(task: Task, spec: RootGoalSpec) -> bool:
    """Return True when the root target parameter has an expansion-ready fact."""
    field = spec.target_field or _param_to_field(spec.target_parameter)
    fact = task.fact_store.active_fact(field)
    if fact is None:
        return False
    return fact_is_expansion_ready(fact)


def workflow_marked_finished(task: Task, spec: RootGoalSpec) -> bool:
    """Return True when authored completion criteria and runtime state indicate finished."""
    completion = spec.completion
    if completion is None:
        return False
    if completion.status != "finished":
        return False
    if completion.when == "target_parameter_satisfied":
        if not workflow_target_satisfied(task, spec):
            return False
    roots = task.goal_store.roots()
    if not roots:
        return False
    root = roots[0]
    if root.satisfaction.status != SatisfactionStatus.SATISFIED:
        return False
    return task.status == TaskStatus.COMPLETED


def completion_spec_from_metadata(root_goal_cfg: dict) -> RootGoalCompletionSpec | None:
    """Parse completion block from raw goal_expansion.root_goal metadata."""
    completion = root_goal_cfg.get("completion")
    if not isinstance(completion, dict):
        return None
    when = str(completion.get("when") or "").strip()
    status = str(completion.get("status") or "").strip()
    if not when and not status:
        return None
    return RootGoalCompletionSpec(when=when, status=status)
