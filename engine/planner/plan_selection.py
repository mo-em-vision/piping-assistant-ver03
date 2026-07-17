"""Read Planner next-field selection from stored EngineeringPlan on a task."""

from __future__ import annotations

from typing import Any

from models.engineering_plan import EngineeringPlan
from models.task import Task, TaskStatus


def engineering_plan_for_task(task: Task) -> EngineeringPlan | None:
    """Rehydrate the canonical stored EngineeringPlan from task outputs."""
    from engine.planner.plan_inspector import engineering_plan_from_dict

    raw = task.outputs.get("engineering_plan")
    if not isinstance(raw, dict):
        return None
    return engineering_plan_from_dict(raw)


def task_has_stored_engineering_plan(task: Task) -> bool:
    return engineering_plan_for_task(task) is not None


def planner_submittable_fields_from_task(task: Task) -> list[str] | None:
    """Return explicit Planner submittable_fields when stored on the EngineeringPlan."""
    raw = task.outputs.get("engineering_plan")
    if not isinstance(raw, dict):
        return None
    strategy_raw = raw.get("input_strategy")
    if not isinstance(strategy_raw, dict) or "submittable_fields" not in strategy_raw:
        return None
    return [str(item) for item in (strategy_raw.get("submittable_fields") or [])]


def planner_next_field_from_task(task: Task) -> str | None:
    """Return input_strategy.next_fields[0] from the stored EngineeringPlan."""
    plan = engineering_plan_for_task(task)
    if plan is None or plan.input_strategy is None:
        return None
    next_fields = plan.input_strategy.next_fields
    if not next_fields:
        return None
    field = str(next_fields[0]).strip()
    return field or None


def planner_next_field_is_submittable(
    task: Task,
    planning: dict[str, Any],
) -> bool:
    """True when planner next field is present in the current submittable projection."""
    field = planner_next_field_from_task(task)
    if field is None:
        return True
    planner_submittable = planner_submittable_fields_from_task(task)
    if planner_submittable is not None:
        return field in planner_submittable
    from engine.navigation import submittable_parameter_ids

    return field in submittable_parameter_ids(task, planning)


def assert_planner_next_submittable(
    task: Task,
    planning: dict[str, Any],
) -> None:
    """Raise when a stored-plan task has a planner next field outside submittable ids."""
    if task.status != TaskStatus.AWAITING_INPUT:
        return
    if not task_has_stored_engineering_plan(task):
        return
    field = planner_next_field_from_task(task)
    if field is None:
        return
    planner_submittable = planner_submittable_fields_from_task(task)
    if planner_submittable is not None:
        submittable = planner_submittable
    else:
        from engine.navigation import submittable_parameter_ids

        submittable = submittable_parameter_ids(task, planning)
    if field not in submittable:
        raise AssertionError(
            f"planner next field {field!r} is not in submittable parameters {submittable!r}"
        )
