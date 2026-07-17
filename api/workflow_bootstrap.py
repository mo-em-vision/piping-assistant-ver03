"""Bootstrap and refresh desktop task planning state from the graph engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.parameter_keys import MATERIAL_GRADE_KEY
from config.loader import CLIConfig
from engine.executor.executor import execute_workflow
from engine.graph.definition_equations import (
    has_execution_trace,
    pending_definition_equation_inputs,
    try_complete_definition_equations,
)
from engine.graph.graph_engine import GraphEngine, normalize_root_id
from engine.planning.definition_anchor import resolve_activated_definition_node
from engine.planning.planning_refresh import (
    PlanningRefreshFinalizeContext,
    refresh_task_planning_state,
)
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN, is_supported_planning_workflow
from engine.state.task_facts import active_facts, store_fact, store_proposed_default
from engine.state.goal_projection import planning_projection
from engine.state.decision_recorder import migrate_path_decision_to_context
from engine.state.execution_context_sync import refresh_execution_context_for_task
from engine.state.state_manager import TaskStateManager
from models.planning import NavigationPhase
from models.task import Task, TaskStatus
from api.material_catalog_service import warm_material_catalog
from api.workflow_timeline import submittable_parameter_ids, sync_timeline_input_order
from engine.graph.workflow_adapters import apply_workflow_planning_defaults
from engine.inspection.operation_tracker import track_operation
from engine.inspection.performance_trace import perf_span


def standards_reader_for_config(config: CLIConfig) -> StandardsReader:
    return StandardsReader(config.standards_root, standard="asme_b31.3")


_PROPOSE_DEFAULTS_ON_FIELDS = frozenset(
    {
        "material_grade",
        "design_temperature",
        "nominal_pipe_size",
        "outside_diameter",
        "pipe_schedule",
        "actual_wall_thickness",
        "joint_category",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "corrosion_allowance",
    }
)

_SUPPORTED_PLANNING_WORKFLOWS = frozenset({PIPE_WALL_THICKNESS_DESIGN, MAWP_DESIGN})  # compat alias


def needs_planning_refresh(task: Task) -> bool:
    """Return True when a supported workflow task should rebuild its goal tree."""
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if not is_supported_planning_workflow(workflow_id):
        return False
    from engine.planner.plan_selection import task_has_stored_engineering_plan

    if not task_has_stored_engineering_plan(task):
        return True
    if not task.goal_store.goals:
        return True
    roots = task.goal_store.roots()
    if not roots:
        return True
    if task.goal_store.children(roots[0].id):
        if has_execution_trace(task):
            return False
        planning = planning_projection(task)
        return planning.get("current_phase") == NavigationPhase.READY.value
    return True


def ensure_task_planning(task: Task, reader: StandardsReader) -> bool:
    """Replan stale bootstrap state. Returns True when planning was refreshed."""
    with track_operation(
        "ensure_task_planning",
        category="planning",
        task_id=task.task_id,
    ):
        with perf_span("ensure_task_planning", "planner", notes=f"task_id={task.task_id}"):
            return _ensure_task_planning_impl(task, reader)


def _ensure_task_planning_impl(task: Task, reader: StandardsReader) -> bool:
    if not needs_planning_refresh(task):
        return False
    from engine.state.goal_migration import migrate_task_goals_from_outputs

    migrate_task_goals_from_outputs(task)
    if not needs_planning_refresh(task):
        return False
    refresh_task_planning(task, reader, propose_defaults=False)
    return True


def refresh_task_planning(
    task: Task,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
    allow_lightweight_refresh: bool = True,
) -> None:
    """Recompute goal tree and active_nodes from current task inputs."""
    with track_operation(
        "refresh_task_planning",
        category="planning",
        task_id=task.task_id,
        propose_defaults=propose_defaults,
    ):
        with perf_span(
            "refresh_task_planning",
            "planner",
            notes=f"propose_defaults={propose_defaults},lightweight={allow_lightweight_refresh}",
        ):
            ctx = refresh_task_planning_state(
                task,
                reader,
                propose_defaults=propose_defaults,
                allow_lightweight_refresh=allow_lightweight_refresh,
            )
            if ctx is not None:
                _finalize_planning_state(
                    task,
                    reader,
                    workflow_id=ctx.workflow_id,
                    root_slug=ctx.root_slug,
                    preview=ctx.preview,
                    graph=ctx.graph,
                    engine=ctx.engine,
                    active_nodes=ctx.active_nodes,
                    uses_micro=ctx.uses_micro,
                )


def _finalize_planning_state(
    task: Task,
    reader: StandardsReader,
    *,
    workflow_id: str,
    root_slug: str,
    preview: Any,
    graph: GraphTools,
    engine: GraphEngine,
    active_nodes: list[str],
    uses_micro: bool,
) -> None:
    from engine.resolution.goal_resolver import resolve_ready_goals
    from engine.state.goal_satisfaction import refresh_goal_satisfaction

    with perf_span("resolve_ready_goals", "planner"):
        if resolve_ready_goals(task, reader.standards_root):
            refresh_goal_satisfaction(task)

    task.active_nodes = active_nodes

    _apply_post_execution_definition_planning(
        task,
        reader,
        execution_order=preview.execution_order,
        graph=graph,
        root_slug=root_slug,
        plan=preview,
    )
    refresh_goal_satisfaction(task)

    migrate_path_decision_to_context(task)
    refresh_execution_context_for_task(task, workflow_id=workflow_id, reader=reader)

    planning = planning_projection(task)
    sync_timeline_input_order(task, planning, reader=reader)
    if MATERIAL_GRADE_KEY in submittable_parameter_ids(task, planning):
        warm_material_catalog(reader.standards_root)

    if uses_micro:
        engine.prefetch(
            reader,
            task_id=task.task_id,
            root_id=root_slug,
            inputs=dict(active_facts(task)),
            horizon=1,
        )



_PIPE_WALL_PRE_EXEC_DEFINITION_FIELDS = frozenset({"corrosion_allowance"})


def _pipe_wall_ready_for_primary_execution(task: Task, planning: dict[str, Any]) -> bool:
    """Allow main thickness execution when only post-thickness definition inputs remain."""
    if has_execution_trace(task):
        return False
    if task.outputs.get("t") is not None or task.outputs.get("required_thickness") is not None:
        return False
    missing = set(planning.get("missing_inputs") or [])
    if not missing:
        return False
    phase_missing = planning.get("phase_missing") or {}
    if not isinstance(phase_missing, dict):
        return False
    definition_missing = set(
        phase_missing.get(NavigationPhase.DEFINITION_EQUATION_COMPLETION.value) or []
    )
    pre_execution_missing = missing - definition_missing
    if pre_execution_missing:
        return False
    return bool(definition_missing & _PIPE_WALL_PRE_EXEC_DEFINITION_FIELDS)


def task_ready_for_execution(task: Task) -> bool:
    if task.status in {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}:
        return False
    workflow = str(task.outputs.get("workflow") or "")
    if not is_supported_planning_workflow(workflow):
        return False

    from engine.planner.graph_navigation import (
        build_graph_navigation_from_plan,
        graph_navigation_has_collectable_missing,
    )
    from engine.planner.plan_selection import (
        engineering_plan_for_task,
        planner_next_field_from_task,
        task_has_stored_engineering_plan,
    )

    if not task_has_stored_engineering_plan(task):
        return False

    plan = engineering_plan_for_task(task)
    if plan is None:
        return False

    if planner_next_field_from_task(task) is not None:
        return False

    nav = build_graph_navigation_from_plan(plan)
    nav_phase = str(nav.get("current_phase") or "")

    if (
        workflow == PIPE_WALL_THICKNESS_DESIGN
        and nav_phase == NavigationPhase.DEFINITION_EQUATION_COMPLETION.value
    ):
        if has_execution_trace(task):
            return False
        thickness_ready = (
            task.outputs.get("t") is not None
            or task.outputs.get("required_thickness") is not None
        )
        if thickness_ready:
            return False

    planning = planning_projection(task)
    if workflow == PIPE_WALL_THICKNESS_DESIGN and _pipe_wall_ready_for_primary_execution(
        task, planning
    ):
        return True

    if has_execution_trace(task):
        return False

    if nav_phase != NavigationPhase.READY.value:
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
            return _maybe_execute_ready_workflow_impl(task_id, manager, reader)


def _maybe_execute_ready_workflow_impl(
    task_id: str,
    manager: TaskStateManager,
    reader: StandardsReader,
) -> Task:
    task = manager.get_task(task_id)
    if not task_ready_for_execution(task):
        return task

    root_slug = normalize_root_id(
        str(task.outputs.get("workflow") or task.outputs.get("selected_root") or PIPE_WALL_THICKNESS_DESIGN)
    )
    execute_workflow(task_id, root_slug, state=manager, reader=reader)
    task = manager.get_task(task_id)
    if root_slug == PIPE_WALL_THICKNESS_DESIGN:
        graph = GraphTools(reader)
        preview = graph.preview_plan(
            task_id=task_id,
            root_id=root_slug,
            inputs=dict(active_facts(task)),
        )
        try_complete_definition_equations(task, reader, preview.execution_order)
        manager.replace_task(task_id, task)
    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task_id, task)
    return manager.get_task(task_id)


def _apply_post_execution_definition_planning(
    task: Task,
    reader: StandardsReader,
    *,
    execution_order: tuple[str, ...] | list[str],
    graph: GraphTools,
    root_slug: str,
    plan: Any,
) -> None:
    if not has_execution_trace(task):
        return

    pending = pending_definition_equation_inputs(task, reader, execution_order)
    if not pending:
        if task.outputs.get("t") is not None or task.outputs.get("required_thickness") is not None:
            try_complete_definition_equations(task, reader, execution_order)
            pending = pending_definition_equation_inputs(task, reader, execution_order)
        if not pending:
            return

    proposed = graph.resolve_and_propose_path_inputs(
        root_slug,
        existing_inputs=dict(active_facts(task)),
        plan=plan,
        task_id=task.task_id,
    )
    for input_id in pending:
        if input_id in proposed and input_id not in active_facts(task):
            store_fact(task, proposed[input_id])

    task.status = TaskStatus.AWAITING_INPUT


def bootstrap_new_task(task: Task, workflow_id: str, config: CLIConfig) -> None:
    """Initialize a newly created task with graph-driven planning state."""
    with track_operation(
        "bootstrap_new_task",
        category="bootstrap",
        task_id=task.task_id,
        workflow_id=workflow_id,
    ):
        _bootstrap_new_task_impl(task, workflow_id, config)


def _bootstrap_new_task_impl(task: Task, workflow_id: str, config: CLIConfig) -> None:
    task.outputs["workflow"] = workflow_id
    task.outputs["selected_root"] = workflow_id

    if not is_supported_planning_workflow(workflow_id):
        from engine.planner.goal_builder import build_goal_tree

        reader = standards_reader_for_config(config)
        build_goal_tree(task, reader)
        return

    reader = standards_reader_for_config(config)
    if task.fact_store.active_fact("straight_pipe_section") is None:
        anchor = resolve_activated_definition_node(reader, workflow_id)
        store_proposed_default(
            task,
            "straight_pipe_section",
            True,
            unit="dimensionless",
            introduced_at_node=anchor,
            default_condition="Applied to a straight section of a pipe.",
        )
    apply_workflow_planning_defaults(task, workflow_id)
    refresh_task_planning(task, reader)
