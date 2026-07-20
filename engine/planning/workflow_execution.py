"""Engine-owned workflow execution gating and dispatch."""

from __future__ import annotations

from typing import Any

from engine.executor.executor import execute_workflow
from engine.graph.definition_equations import (
    has_execution_trace,
    try_complete_definition_equations,
)
from engine.graph.graph_engine import normalize_root_id
from engine.inspection.operation_tracker import track_operation
from engine.inspection.performance_trace import perf_span
from engine.planner.graph_navigation import (
    build_graph_navigation_from_plan,
    graph_navigation_has_collectable_missing,
)
from engine.planner.plan_selection import (
    engineering_plan_for_task,
    planner_next_field_from_task,
    task_has_stored_engineering_plan,
)
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.router import is_supported_planning_workflow
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import active_facts
from models.engineering_plan import PlanRequirement
from models.planning import NavigationPhase
from models.task import Task, TaskStatus


def _missing_collectable_field(req: PlanRequirement) -> str | None:
    if req.activation_status != "active":
        return None
    if req.status != "missing":
        return None
    if req.requirement_class not in {"user_input", "branch_decision"}:
        return None
    if req.question_spec is None:
        return None
    if req.question_spec.ask_policy in {"ask_later", "do_not_ask", "ask_if_needed"}:
        return None
    return req.question_spec.field


def _ready_for_primary_execution_with_deferred_definition(task: Task) -> bool:
    """Allow primary execution when only ask_later definition-phase inputs remain."""
    from engine.planner.workflow_goal_metadata import goal_output_value_for_task

    if has_execution_trace(task):
        return False
    if goal_output_value_for_task(task) is not None:
        return False

    plan = engineering_plan_for_task(task)
    if plan is None:
        return False

    collectable: list[str] = []
    deferred_definition: list[str] = []
    for req in plan.requirements.values():
        field = _missing_collectable_field(req)
        if not field:
            continue
        if (
            req.phase == NavigationPhase.DEFINITION_EQUATION_COMPLETION.value
            and req.question_spec
            and req.question_spec.ask_policy == "ask_later"
        ):
            deferred_definition.append(field)
        else:
            collectable.append(field)

    if collectable:
        return False
    return bool(deferred_definition)


def task_ready_for_execution(task: Task) -> bool:
    """Return True when phased navigation has collected all required pre-execution inputs."""
    if task.status in {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}:
        return False
    workflow = str(task.outputs.get("workflow") or "")
    if not is_supported_planning_workflow(workflow):
        return False

    if not task_has_stored_engineering_plan(task):
        return False

    plan = engineering_plan_for_task(task)
    if plan is None:
        return False

    if planner_next_field_from_task(task) is not None:
        return False

    if _ready_for_primary_execution_with_deferred_definition(task):
        return True

    if has_execution_trace(task):
        return False

    nav = build_graph_navigation_from_plan(plan)
    if str(nav.get("current_phase") or "") != NavigationPhase.READY.value:
        return False

    return not graph_navigation_has_collectable_missing(nav)


def maybe_execute_ready_workflow(
    task_id: str,
    manager: TaskStateManager,
    reader: StandardsReader,
) -> Task:
    """Run the engineering executor when phased navigation has collected all required inputs."""
    with track_operation("maybe_execute_ready_workflow", category="execution", task_id=task_id):
        task = manager.get_task(task_id)
        ready = task_ready_for_execution(task)
        with perf_span(
            "maybe_execute_ready_workflow",
            "execution",
            notes=f"ready={ready}",
            skipped=not ready,
        ):
            if not ready:
                return task
            return _execute_ready_workflow(task_id, manager, reader)


def _execute_ready_workflow(
    task_id: str,
    manager: TaskStateManager,
    reader: StandardsReader,
) -> Task:
    from engine.planning.workflow_initiation import refresh_workflow_planning

    task = manager.get_task(task_id)
    if not task_ready_for_execution(task):
        return task

    root_slug = normalize_root_id(
        str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    )
    execute_workflow(task_id, root_slug, state=manager, reader=reader)
    task = manager.get_task(task_id)

    graph = GraphTools(reader)
    preview = graph.preview_plan(
        task_id=task_id,
        root_id=root_slug,
        inputs=dict(active_facts(task)),
    )
    try_complete_definition_equations(task, reader, preview.execution_order)
    manager.replace_task(task_id, task)

    refresh_workflow_planning(task, reader, propose_defaults=False)
    manager.replace_task(task_id, task)
    return manager.get_task(task_id)
