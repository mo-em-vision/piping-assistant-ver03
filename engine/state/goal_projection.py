"""Backward-compatible projections from goal_store for API consumers."""

from __future__ import annotations

from models.agent import AgentAction
from models.goal import Goal, GoalClass, SatisfactionStatus, goal_parameter_key
from models.planning import NavigationPhase
from models.task import Task


def _goals_by_phase(task: Task) -> dict[str, list[Goal]]:
    by_phase: dict[str, list[Goal]] = {}
    for goal in task.goal_store.goals.values():
        phase = str(goal.metadata.get("phase") or NavigationPhase.READY.value)
        by_phase.setdefault(phase, []).append(goal)
    return by_phase


def missing_input_keys(task: Task) -> list[str]:
    """Blocked input/lookup goals mapped to runtime parameter keys."""
    keys: list[str] = []
    for goal in task.goal_store.goals.values():
        if goal.goal_class not in {GoalClass.INPUT, GoalClass.LOOKUP}:
            continue
        if goal.satisfaction.status == SatisfactionStatus.SATISFIED:
            continue
        if goal.satisfaction.status in {
            SatisfactionStatus.BLOCKED,
            SatisfactionStatus.PENDING,
            SatisfactionStatus.READY,
        }:
            keys.append(goal_parameter_key(goal))
    return sorted(set(keys))


def missing_assumption_keys(task: Task) -> list[str]:
    keys: list[str] = []
    for goal in task.goal_store.goals.values():
        phase = str(goal.metadata.get("phase") or "")
        if phase not in {
            NavigationPhase.EXPANSION_ASSUMPTIONS.value,
            NavigationPhase.PATH_DECISIONS.value,
            NavigationPhase.EXECUTION_ASSUMPTIONS.value,
        }:
            continue
        if goal.satisfaction.status == SatisfactionStatus.SATISFIED:
            continue
        if goal.goal_class in {
            GoalClass.INPUT,
            GoalClass.SELECTION,
            GoalClass.LOOKUP,
        }:
            keys.append(goal_parameter_key(goal))
    return sorted(set(keys))


def missing_execution_assumption_keys(task: Task) -> list[str]:
    keys: list[str] = []
    for goal in task.goal_store.goals.values():
        phase = str(goal.metadata.get("phase") or "")
        if phase != NavigationPhase.EXECUTION_ASSUMPTIONS.value:
            continue
        if goal.satisfaction.status == SatisfactionStatus.SATISFIED:
            continue
        if goal.goal_class in {
            GoalClass.INPUT,
            GoalClass.SELECTION,
            GoalClass.LOOKUP,
        }:
            keys.append(goal_parameter_key(goal))
    return sorted(set(keys))


def current_phase(task: Task) -> str:
    phase_order = [p.value for p in NavigationPhase]
    by_phase = _goals_by_phase(task)
    for phase in phase_order:
        goals = by_phase.get(phase, [])
        if not goals:
            continue
        actionable = [
            g
            for g in goals
            if g.satisfaction.status
            not in {SatisfactionStatus.SATISFIED, SatisfactionStatus.SUPERSEDED}
            and g.satisfaction.status != SatisfactionStatus.BLOCKED
        ]
        if actionable:
            return phase
    return NavigationPhase.READY.value


def phase_missing(task: Task) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    roots = task.goal_store.roots()
    if not roots:
        return result
    children = [
        goal
        for goal in task.goal_store.children(roots[0].id)
        if goal.goal_class
        in {
            GoalClass.INPUT,
            GoalClass.SELECTION,
            GoalClass.LOOKUP,
        }
        and goal.satisfaction.status != SatisfactionStatus.SATISFIED
        and goal.satisfaction.status != SatisfactionStatus.BLOCKED
    ]
    children.sort(
        key=lambda goal: (int(goal.metadata.get("order") or 10_000), goal.key),
    )
    for goal in children:
        phase = str(goal.metadata.get("phase") or NavigationPhase.READY.value)
        key = goal_parameter_key(goal)
        bucket = result.setdefault(phase, [])
        if key not in bucket:
            bucket.append(key)
    return result


def phase_questions(task: Task) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for goal in task.goal_store.goals.values():
        if goal.question is None:
            continue
        phase = str(goal.metadata.get("phase") or NavigationPhase.READY.value)
        key = goal_parameter_key(goal)
        result.setdefault(phase, {})[key] = goal.question.prompt
    return result


def planner_action(task: Task) -> str:
    if missing_input_keys(task) or missing_assumption_keys(task):
        return AgentAction.REQUEST_INPUT.value
    blocked = task.goal_store.blocked_goals()
    if blocked:
        return AgentAction.CLARIFY.value
    return AgentAction.PROPOSE_PATH.value


def root_goal_name(task: Task) -> str | None:
    roots = task.goal_store.roots()
    if roots:
        return roots[0].name
    return None


def goal_summary_dict(task: Task) -> dict[str, object]:
    """Planning-compatible summary derived from goal_store."""
    roots = task.goal_store.roots()
    root = roots[0] if roots else None
    return {
        "goal": root.name if root else None,
        "intent": str(task.outputs.get("workflow") or ""),
        "missing_inputs": missing_input_keys(task),
        "missing_assumptions": missing_assumption_keys(task),
        "missing_execution_assumptions": missing_execution_assumption_keys(task),
        "current_phase": current_phase(task),
        "phase_missing": phase_missing(task),
        "phase_questions": phase_questions(task),
        "action": planner_action(task),
    }


def planning_projection(task: Task) -> dict[str, object]:
    """Full planning-compatible dict derived from goal_store (replaces planning_summary)."""
    summary = goal_summary_dict(task)
    roots = task.goal_store.roots()
    root = roots[0] if roots else None
    summary["selected_root"] = str(
        task.outputs.get("selected_root") or task.outputs.get("workflow") or ""
    )
    summary["selected_nodes"] = list(
        (root.metadata.get("selected_nodes") if root else None)
        or task.outputs.get("selected_nodes")
        or []
    )
    summary["active_definition_node"] = task.outputs.get("active_definition_node")
    summary["path_decision"] = task.outputs.get("path_decision")
    summary["phase_allowed_fields"] = task.outputs.get("phase_allowed_fields") or {}
    summary["graph_input_order"] = task.outputs.get("graph_input_order")
    summary["graph_step_titles"] = task.outputs.get("graph_step_titles")
    summary["collection_field_order"] = task.outputs.get("collection_field_order")
    summary["confidence"] = 1.0
    engineering_plan_view = task.outputs.get("engineering_plan_view")
    canonical_plan = task.outputs.get("engineering_plan")
    if isinstance(engineering_plan_view, dict):
        summary["engineering_plan_view"] = engineering_plan_view
    elif isinstance(canonical_plan, dict):
        from engine.planner.plan_inspector import build_engineering_plan_view_from_dict

        rebuilt = build_engineering_plan_view_from_dict(canonical_plan)
        if rebuilt:
            summary["engineering_plan_view"] = rebuilt
    if isinstance(canonical_plan, dict) and "plan_id" in canonical_plan:
        summary["engineering_plan"] = canonical_plan
    planner_summary = task.outputs.get("planner_inspector_summary")
    if isinstance(planner_summary, dict):
        summary["planner_inspector_summary"] = planner_summary
    return summary


def goals_to_api_dict(task: Task) -> dict[str, dict]:
    from models.goal import goal_to_dict

    return {
        gid: goal_to_dict(goal)
        for gid, goal in task.goal_store.goals.items()
    }


def legacy_goal_map_for_task(task: Task) -> dict[str, dict]:
    """Backward-compatible goal map; prefer embedded plan.legacy_goal_map when present."""
    raw = task.outputs.get("engineering_plan")
    if isinstance(raw, dict):
        embedded = raw.get("legacy_goal_map")
        if isinstance(embedded, dict):
            return {str(key): dict(value) for key, value in embedded.items()}
    return goals_to_api_dict(task)
