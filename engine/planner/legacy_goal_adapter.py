"""Apply EngineeringPlan to legacy GoalStore for backward-compatible consumers."""

from __future__ import annotations

from engine.state.goal_satisfaction import refresh_goal_satisfaction
from engine.state.task_goals import clear_goal_store, expand_goal, store_goal
from models.engineering_plan import EngineeringPlan, PlanRequirement
from models.goal import (
    Goal,
    GoalClass,
    RequiredFactRef,
    SatisfactionStatus,
    calculation_goal,
    input_goal,
    lookup_goal,
    selection_goal,
)
from models.goal_store import GoalStore
from models.task import Task


def _goal_class_for_requirement(req: PlanRequirement) -> GoalClass:
    if req.requirement_class == "branch_decision":
        return GoalClass.SELECTION
    if req.requirement_class == "table_lookup":
        return GoalClass.LOOKUP
    if req.requirement_class in {"equation_result", "derived_value", "validation_check"}:
        return GoalClass.CALCULATION
    return GoalClass.INPUT


def _status_for_requirement(status: str) -> SatisfactionStatus:
    mapping = {
        "missing": SatisfactionStatus.READY,
        "ready": SatisfactionStatus.READY,
        "resolved": SatisfactionStatus.SATISFIED,
        "blocked": SatisfactionStatus.BLOCKED,
        "not_applicable": SatisfactionStatus.SUPERSEDED,
    }
    return mapping.get(status, SatisfactionStatus.PENDING)


def _goal_for_requirement(
    req: PlanRequirement,
    *,
    task: Task,
    workflow_id: str,
    root_id: str,
    order: int,
) -> Goal:
    label = req.question_spec.label if req.question_spec else req.field.replace("_", " ").title()
    goal_class = _goal_class_for_requirement(req)
    key_prefix = {
        GoalClass.INPUT: "input",
        GoalClass.SELECTION: "select",
        GoalClass.LOOKUP: "lookup",
        GoalClass.CALCULATION: "derive",
    }[goal_class]
    key = f"{key_prefix}-{req.field}"

    required_facts = [
        dep.replace("REQ-", "").replace("_lookup", "").replace("_eq", "")
        for dep in req.depends_on
    ]

    if goal_class == GoalClass.LOOKUP:
        goal = lookup_goal(
            key=key,
            name=label,
            target_parameter=req.field,
            task_id=task.task_id,
            required_facts=required_facts,
            workflow_id=workflow_id,
            parent_goal=root_id,
            phase=req.phase,
            order=order,
        )
    elif goal_class == GoalClass.SELECTION:
        goal = selection_goal(
            key=key,
            name=label,
            target_parameter=req.field,
            task_id=task.task_id,
            prompt="",
            workflow_id=workflow_id,
            parent_goal=root_id,
            phase=req.phase,
            order=order,
        )
    else:
        goal = input_goal(
            key=key,
            name=label,
            target_parameter=req.field,
            task_id=task.task_id,
            prompt="",
            workflow_id=workflow_id,
            parent_goal=root_id,
            phase=req.phase,
            order=order,
        )

    goal.id = req.id
    goal.satisfaction.status = _status_for_requirement(req.status)
    goal.required_facts = [RequiredFactRef(parameter=f) for f in required_facts if f]
    if req.question_spec:
        goal.metadata["question_spec"] = req.question_spec.to_dict()
    if req.alternatives:
        goal.metadata["alternatives"] = [alt.to_dict() for alt in req.alternatives]
    if req.resolution:
        goal.metadata["resolution"] = dict(req.resolution)

    return goal


def _attach_dependency_edges(task: Task, plan: EngineeringPlan) -> None:
    goal_by_id = task.goal_store.goals
    for edge in plan.dependencies:
        from_goal = goal_by_id.get(edge.from_id)
        to_goal = goal_by_id.get(edge.to_id)
        if from_goal is None or to_goal is None:
            continue
        from_goal.edges.append(
            {"from": from_goal.id, "to": to_goal.id, "type": edge.type}
        )


def apply_engineering_plan_to_goal_store(task: Task, plan: EngineeringPlan) -> GoalStore:
    """Replace task goal_store with goals derived from a normalized engineering plan."""
    workflow_id = plan.workflow_id
    clear_goal_store(task)

    root = calculation_goal(
        key=plan.root_goal.key,
        name=plan.root_goal.title,
        target_parameter=plan.root_goal.target_field,
        task_id=task.task_id,
        workflow_id=workflow_id,
    )
    root.id = plan.root_goal.id
    root.satisfaction.status = (
        SatisfactionStatus.READY
        if plan.root_goal.status == "ready"
        else SatisfactionStatus.BLOCKED
        if plan.root_goal.status == "blocked"
        else SatisfactionStatus.PENDING
    )
    root.state.blocked_by = list(plan.root_goal.blocked_by)
    root.metadata["required_outputs"] = list(plan.root_goal.required_outputs)
    store_goal(task, root, as_root=True)

    ordered_requirements: list[PlanRequirement] = []
    for phase in plan.phases:
        for req_id_value in phase.requirement_ids:
            req = plan.requirements.get(req_id_value)
            if req is None or req.status == "not_applicable":
                continue
            if req.requirement_class not in {"user_input", "branch_decision"}:
                continue
            if req.id in {"REQ-outside_diameter_lookup"}:
                continue
            if req.field in {
                "allowable_stress",
                "weld_joint_efficiency",
                "temperature_coefficient_Y",
                "weld_strength_reduction_factor_W",
                "metallurgical_group",
                "required_wall_thickness",
                "minimum_required_thickness",
            }:
                continue
            if req.status == "resolved":
                continue
            ordered_requirements.append(req)
    seen: set[str] = set()
    order = 0
    for req in ordered_requirements:
        if req.id in seen:
            continue
        seen.add(req.id)
        order += 1
        child = _goal_for_requirement(
            req,
            task=task,
            workflow_id=workflow_id,
            root_id=root.id,
            order=order,
        )
        expand_goal(task, root.id, child)

    _attach_dependency_edges(task, plan)
    refresh_goal_satisfaction(task)
    return task.goal_store


def store_engineering_plan_on_task(task: Task, plan: EngineeringPlan) -> None:
    from engine.planner.graph_navigation import build_graph_navigation_from_plan
    from engine.planner.plan_inspector import (
        build_engineering_plan_view,
        build_planner_inspector_summary,
    )

    task.outputs["engineering_plan"] = plan.to_dict()
    view = build_engineering_plan_view(plan)
    task.outputs["engineering_plan_view"] = view
    task.outputs["planner_inspector_summary"] = build_planner_inspector_summary(plan)
    task.outputs["graph_navigation"] = build_graph_navigation_from_plan(plan)
