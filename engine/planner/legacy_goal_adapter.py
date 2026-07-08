"""Apply EngineeringPlan to legacy GoalStore for backward-compatible consumers."""

from __future__ import annotations

from typing import Any

from engine.planner.plan_dependencies import build_plan_dependencies
from engine.state.goal_satisfaction import refresh_goal_satisfaction
from engine.state.task_goals import clear_goal_store, expand_goal, store_goal
from models.engineering_plan import (
    EngineeringPlan,
    PlanDependency,
    PlanRequirement,
    requirement_key_for_class,
)
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
    task_id: str,
    workflow_id: str,
    root_id: str,
    order: int,
) -> Goal:
    label = req.resolved_title()
    goal_class = _goal_class_for_requirement(req)
    key = req.resolved_key()

    required_facts = [
        dep.replace("REQ-", "").replace("_lookup", "").replace("_eq", "")
        for dep in req.depends_on
    ]

    if goal_class == GoalClass.LOOKUP:
        goal = lookup_goal(
            key=key,
            name=label,
            target_parameter=req.field,
            task_id=task_id,
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
            task_id=task_id,
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
            task_id=task_id,
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


def _root_goal_from_plan(plan: EngineeringPlan) -> Goal:
    root = calculation_goal(
        key=plan.root_goal.key,
        name=plan.root_goal.title,
        target_parameter=plan.root_goal.target_field,
        task_id=plan.task_id,
        workflow_id=plan.workflow_id,
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
    if plan.root_goal.provisional_blocked_by:
        root.metadata["provisional_blocked_by"] = list(plan.root_goal.provisional_blocked_by)
    return root


def _attach_dependency_edges_to_goals(
    goals: dict[str, Any],
    dependencies: list[PlanDependency],
) -> None:
    for edge in dependencies:
        from_goal = goals.get(edge.from_id)
        if from_goal is None:
            continue
        from_goal.edges.append(
            {"from": edge.from_id, "to": edge.to_id, "type": edge.type}
        )


def build_legacy_goal_map(plan: EngineeringPlan) -> dict[str, Any]:
    """Backward-compatible flat GOAL-*/REQ-* map derived from a normalized plan."""
    from models.goal import goal_to_dict

    root = _root_goal_from_plan(plan)
    goals: dict[str, Goal] = {root.id: root}

    order = 0
    seen: set[str] = set()
    for phase in plan.phases:
        for req_id_value in phase.requirement_ids:
            req = plan.requirements.get(req_id_value)
            if req is None or req.id in seen:
                continue
            seen.add(req.id)
            order += 1
            child = _goal_for_requirement(
                req,
                task_id=plan.task_id,
                workflow_id=plan.workflow_id,
                root_id=root.id,
                order=order,
            )
            goals[child.id] = child

    for req_id_value, req in plan.requirements.items():
        if req_id_value in seen:
            continue
        order += 1
        child = _goal_for_requirement(
            req,
            task_id=plan.task_id,
            workflow_id=plan.workflow_id,
            root_id=root.id,
            order=order,
        )
        goals[child.id] = child

    _attach_dependency_edges_to_goals(goals, plan.dependencies)

    return {goal_id: goal_to_dict(goal) for goal_id, goal in goals.items()}


def enrich_plan_requirements(requirements: dict[str, PlanRequirement]) -> None:
    """Normalize requirement identity fields; no legacy goal shape on PlanRequirement."""
    from engine.reference.parameter_keys import load_parameter_node_metadata
    from models.engineering_plan import requirement_key_for_class

    for req in requirements.values():
        req.key = requirement_key_for_class(req.requirement_class, req.field)
        if not req.title and req.parameter_node_id:
            meta = load_parameter_node_metadata(req.parameter_node_id)
            if meta and meta.get("name"):
                req.title = str(meta["name"])
        if not req.title:
            req.title = req.resolved_title()


def finalize_engineering_plan(
    plan: EngineeringPlan,
    *,
    source: str = "engineering_plan_builder",
) -> EngineeringPlan:
    """Attach legacy adapter and normalize debug metadata before persistence."""
    enrich_plan_requirements(plan.requirements)
    plan.dependencies = build_plan_dependencies(
        plan.requirements,
        workflow_id=plan.workflow_id,
    )
    plan.legacy_goal_map = build_legacy_goal_map(plan)
    if plan.debug:
        warnings = list(plan.debug.get("warnings") or [])
        warnings.extend(plan.debug.get("validation_warnings") or [])
        warnings.extend(plan.debug.get("validation_errors") or [])
        plan.debug = {
            "warnings": warnings,
            "source": str(plan.debug.get("source") or source),
        }
    return plan


def _attach_dependency_edges(task: Task, plan: EngineeringPlan) -> None:
    _attach_dependency_edges_to_goals(task.goal_store.goals, plan.dependencies)


def _requirement_ids_to_goal_keys(
    requirement_ids: list[str],
    store: GoalStore,
    *,
    requirements: dict[str, PlanRequirement] | None = None,
) -> list[str]:
    keys: list[str] = []
    for requirement_id in requirement_ids:
        goal = store.get(requirement_id)
        if goal is not None:
            keys.append(goal.key)
            continue
        if requirements is not None:
            req = requirements.get(requirement_id)
            if req is not None:
                keys.append(req.resolved_key())
                continue
        keys.append(requirement_id)
    return keys


def _sync_root_blocking_from_plan(task: Task, plan: EngineeringPlan) -> None:
    roots = task.goal_store.roots()
    if not roots:
        return
    root = roots[0]
    root.state.blocked_by = _requirement_ids_to_goal_keys(
        plan.root_goal.blocked_by,
        task.goal_store,
        requirements=plan.requirements,
    )
    if plan.root_goal.provisional_blocked_by:
        root.metadata["provisional_blocked_by"] = _requirement_ids_to_goal_keys(
            plan.root_goal.provisional_blocked_by,
            task.goal_store,
            requirements=plan.requirements,
        )
    else:
        root.metadata.pop("provisional_blocked_by", None)


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
    if plan.root_goal.provisional_blocked_by:
        root.metadata["provisional_blocked_by"] = list(plan.root_goal.provisional_blocked_by)
    store_goal(task, root, as_root=True)

    ordered_requirements: list[PlanRequirement] = []
    for phase in plan.phases:
        for req_id_value in phase.requirement_ids:
            req = plan.requirements.get(req_id_value)
            if req is None or req.status == "not_applicable":
                continue
            if req.activation_status != "active":
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
                "calculation_report",
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
            task_id=task.task_id,
            workflow_id=workflow_id,
            root_id=root.id,
            order=order,
        )
        expand_goal(task, root.id, child)

    _attach_dependency_edges(task, plan)
    refresh_goal_satisfaction(task)
    _sync_root_blocking_from_plan(task, plan)
    return task.goal_store


def store_engineering_plan_on_task(task: Task, plan: EngineeringPlan) -> None:
    from engine.inspection.performance_trace import perf_span
    from engine.planner.graph_navigation import build_graph_navigation_from_plan
    from engine.planner.plan_inspector import (
        build_engineering_plan_view,
        build_planner_inspector_summary,
    )

    with perf_span("store_engineering_plan_on_task", "planner"):
        finalized = finalize_engineering_plan(plan)
        with perf_span("engineering_plan_to_dict", "planner"):
            task.outputs["engineering_plan"] = finalized.to_dict()
        view = build_engineering_plan_view(finalized)
        task.outputs["engineering_plan_view"] = view
        with perf_span("planner_inspector_summary", "planner"):
            task.outputs["planner_inspector_summary"] = build_planner_inspector_summary(finalized)
        task.outputs["graph_navigation"] = build_graph_navigation_from_plan(finalized)
