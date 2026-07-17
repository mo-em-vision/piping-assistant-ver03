"""Synchronize EngineeringPlan-derived projections on a task."""

from __future__ import annotations

from engine.planner.plan_selection import engineering_plan_for_task
from models.engineering_plan import EngineeringPlan
from models.goal import GoalClass, SatisfactionStatus, goal_parameter_key
from models.task import Task


def sync_plan_projections(task: Task) -> bool:
    """Project EngineeringPlan into goal_store only.

    Does not touch execution_context runtime state (facts, validation, status).
    Derived navigation caches (graph_navigation, engineering_plan_view, …) are
    rebuilt at read time — not persisted on task.outputs.
    """
    plan = engineering_plan_for_task(task)
    if plan is None:
        return False

    from engine.planner.legacy_goal_adapter import apply_engineering_plan_to_goal_store

    apply_engineering_plan_to_goal_store(task, plan)
    return True


def plan_projection_is_consistent(task: Task) -> bool:
    """Return True when goal_store mirrors active unresolved plan requirements."""
    plan = engineering_plan_for_task(task)
    if plan is None:
        return True

    expected_fields = _expected_projection_fields(plan)
    actual_fields = _actual_projection_fields(task)
    return expected_fields == actual_fields


def _expected_projection_fields(plan: EngineeringPlan) -> frozenset[str]:
    _skipped_fields = {
        "allowable_stress",
        "weld_joint_efficiency",
        "temperature_coefficient_Y",
        "weld_joint_strength_reduction_factor_W",
        "metallurgical_group",
        "required_wall_thickness",
        "minimum_required_thickness",
        "calculation_report",
    }
    _skipped_req_ids = {"REQ-outside_diameter_lookup"}
    fields: set[str] = set()
    for phase in plan.phases:
        for req_id in phase.requirement_ids:
            req = plan.requirements.get(req_id)
            if req is None or req.status in {"resolved", "not_applicable"}:
                continue
            if req.activation_status != "active":
                continue
            if req.requirement_class not in {"user_input", "branch_decision"}:
                continue
            if req.id in _skipped_req_ids:
                continue
            if req.field in _skipped_fields:
                continue
            if req.field:
                fields.add(req.field)
    return frozenset(fields)


def _actual_projection_fields(task: Task) -> frozenset[str]:
    roots = task.goal_store.roots()
    if not roots:
        return frozenset()
    fields: set[str] = set()
    for goal in task.goal_store.children(roots[0].id):
        if goal.goal_class not in {GoalClass.INPUT, GoalClass.SELECTION, GoalClass.LOOKUP}:
            continue
        if goal.satisfaction.status in {
            SatisfactionStatus.SATISFIED,
            SatisfactionStatus.BLOCKED,
            SatisfactionStatus.SUPERSEDED,
        }:
            continue
        fields.add(goal_parameter_key(goal))
    return frozenset(fields)
