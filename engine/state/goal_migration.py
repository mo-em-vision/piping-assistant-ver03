"""Migrate legacy planning_summary dicts to GoalStore."""

from __future__ import annotations

from typing import Any

from engine.reference.param_resolver import resolve_parameter_id
from models.goal import (
    Goal,
    calculation_goal,
    input_goal,
    lookup_goal,
    selection_goal,
)
from models.goal_store import GoalStore
from models.planning import NavigationPhase


def goals_from_planning_summary(
    summary: dict[str, Any],
    *,
    task_id: str,
    workflow_id: str | None = None,
) -> GoalStore:
    store = GoalStore()
    goal_name = str(summary.get("goal") or workflow_id or "Engineering goal")
    root = calculation_goal(
        key="verify-engineering-goal",
        name=goal_name,
        target_parameter="required-wall-thickness",
        task_id=task_id,
        workflow_id=workflow_id,
    )
    root.provenance.created_from_user_intent = str(summary.get("intent") or workflow_id or "")
    store.append_goal(root, as_root=True)

    phase_missing: dict[str, list[str]] = dict(summary.get("phase_missing") or {})
    phase_questions: dict[str, dict[str, str]] = dict(summary.get("phase_questions") or {})

    order = 0
    seen: set[str] = set()
    for phase, fields in phase_missing.items():
        questions = phase_questions.get(phase, {})
        for field_id in fields:
            seen.add(str(field_id))
            prompt = questions.get(field_id) or f"Provide {field_id.replace('_', ' ')}"
            order += 1
            child = _goal_for_field(
                field_id=str(field_id),
                phase=phase,
                prompt=prompt,
                task_id=task_id,
                workflow_id=workflow_id,
                parent_goal=root.id,
                order=order,
            )
            store.append_goal(child)
            store.link_child(root.id, child.id)

    if not phase_missing:
        for field_id in summary.get("missing_inputs") or []:
            if str(field_id) in seen:
                continue
            prompt = f"Provide {str(field_id).replace('_', ' ')}"
            order += 1
            child = _goal_for_field(
                field_id=str(field_id),
                phase=str(summary.get("current_phase") or NavigationPhase.PARAMETER_GATHERING.value),
                prompt=prompt,
                task_id=task_id,
                workflow_id=workflow_id,
                parent_goal=root.id,
                order=order,
            )
            store.append_goal(child)
            store.link_child(root.id, child.id)

    return store


def _goal_for_field(
    *,
    field_id: str,
    phase: str,
    prompt: str,
    task_id: str,
    workflow_id: str | None,
    parent_goal: str,
    order: int,
) -> Goal:
    if phase == NavigationPhase.PATH_DECISIONS.value and field_id in {
        "pressure_loading",
        "geometry_input_mode",
        "d_input_mode",
    }:
        return selection_goal(
            key=f"select-{field_id}",
            name=prompt,
            target_parameter=field_id,
            task_id=task_id,
            prompt=prompt,
            workflow_id=workflow_id,
            parent_goal=parent_goal,
            phase=phase,
            order=order,
        )
    if field_id in {
        "allowable_stress",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
    }:
        return lookup_goal(
            key=f"lookup-{field_id}",
            name=prompt,
            target_parameter=field_id,
            task_id=task_id,
            required_facts=["material", "design_temperature"],
            workflow_id=workflow_id,
            parent_goal=parent_goal,
            phase=phase,
            order=order,
        )
    return input_goal(
        key=f"input-{field_id}",
        name=prompt,
        target_parameter=field_id,
        task_id=task_id,
        prompt=prompt,
        workflow_id=workflow_id,
        parent_goal=parent_goal,
        phase=phase,
        order=order,
    )


def migrate_task_goals_from_outputs(task: Any) -> None:
    """Populate goal_store from legacy planning_summary when empty."""
    if task.goal_store.goals:
        return
    summary = task.outputs.get("planning_summary")
    if not isinstance(summary, dict):
        return
    workflow_id = str(task.outputs.get("workflow") or "")
    task.execution_context.goal_store = goals_from_planning_summary(
        summary,
        task_id=task.task_id,
        workflow_id=workflow_id or None,
    )
    if "planning_summary" in task.outputs:
        del task.outputs["planning_summary"]
