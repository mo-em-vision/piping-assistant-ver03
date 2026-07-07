"""Opportunistically resolve lookup goals during task replanning."""

from __future__ import annotations

from pathlib import Path

from engine.executor.allowable_stress_resolver import apply_allowable_stress_lookup
from engine.executor.coefficient_lookup import apply_coefficient_lookups
from engine.executor.metallurgical_group_resolver import apply_metallurgical_group_lookup
from engine.state.goal_satisfaction import refresh_goal_satisfaction
from models.fact import fact_scalar_value
from models.task import Task


def _facts_snapshot(task: Task) -> dict[str, object]:
    return {
        key: fact_scalar_value(fact)
        for key, fact in task.fact_store.active_facts().items()
    }


def resolve_ready_goals(task: Task, standards_root: Path, *, max_passes: int = 3) -> bool:
    """Run lookup resolvers when prerequisites exist; refresh goal satisfaction.

    Returns True when any fact values changed during resolution.
    """
    changed = False
    for _ in range(max_passes):
        before = _facts_snapshot(task)
        apply_allowable_stress_lookup(task, standards_root)
        apply_metallurgical_group_lookup(task, standards_root)
        apply_coefficient_lookups(task, standards_root)
        refresh_goal_satisfaction(task)
        after = _facts_snapshot(task)
        if before != after:
            changed = True
        else:
            break
    return changed
