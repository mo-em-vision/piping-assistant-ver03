"""Bootstrap and refresh desktop task planning state — thin API adapter."""

from __future__ import annotations

from typing import Any

from config.loader import CLIConfig
from engine.planning.definition_anchor import resolve_activated_definition_node
from engine.planning.workflow_execution import (
    maybe_execute_ready_workflow,
    task_ready_for_execution,
)
from engine.planning.workflow_initiation import (
    finalize_planning_refresh,
    initiate_workflow_task,
    refresh_workflow_planning,
)
from engine.reference.parameter_keys import MATERIAL_GRADE_KEY
from engine.reference.standards_reader import StandardsReader
from engine.router import PIPE_WALL_THICKNESS_DESIGN, MAWP_DESIGN, is_supported_planning_workflow
from engine.state.state_manager import TaskStateManager
from models.task import Task

_SUPPORTED_PLANNING_WORKFLOWS = frozenset({PIPE_WALL_THICKNESS_DESIGN, MAWP_DESIGN})  # compat alias


def standards_reader_for_config(config: CLIConfig) -> StandardsReader:
    return StandardsReader(config.standards_root, standard="asme_b31.3")


def needs_planning_refresh(task: Task) -> bool:
    """Return True when a supported workflow task should rebuild its goal tree."""
    from engine.graph.definition_equations import has_execution_trace
    from engine.planner.plan_selection import task_has_stored_engineering_plan
    from engine.state.goal_projection import planning_projection
    from models.planning import NavigationPhase

    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if not is_supported_planning_workflow(workflow_id):
        return False
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
    from engine.inspection.operation_tracker import track_operation
    from engine.inspection.performance_trace import perf_span

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
    from api.material_catalog_service import warm_material_catalog
    from engine.inspection.operation_tracker import track_operation
    from engine.inspection.performance_trace import perf_span
    from engine.navigation.submittable_projection import submittable_parameter_ids
    from engine.planning.planning_refresh import refresh_task_planning_state
    from engine.state.goal_projection import planning_projection

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
                finalize_planning_refresh(task, reader, ctx)
                planning = planning_projection(task)
                if MATERIAL_GRADE_KEY in submittable_parameter_ids(task, planning):
                    warm_material_catalog(reader.standards_root)


def _finalize_planning_state_legacy(
    task: Task,
    reader: StandardsReader,
    *,
    workflow_id: str,
    root_slug: str,
    preview: Any,
    graph: Any,
    engine: Any,
    active_nodes: list[str],
    uses_micro: bool,
) -> None:
    from engine.planning.planning_refresh import PlanningRefreshFinalizeContext

    finalize_planning_refresh(
        task,
        reader,
        PlanningRefreshFinalizeContext(
            workflow_id=workflow_id,
            root_slug=root_slug,
            preview=preview,
            graph=graph,
            engine=engine,
            active_nodes=active_nodes,
            uses_micro=uses_micro,
        ),
    )


# Backward-compatible alias used by tests and profile scripts.
_finalize_planning_state = _finalize_planning_state_legacy


def bootstrap_new_task(task: Task, workflow_id: str, config: CLIConfig) -> None:
    """Initialize a newly created task with graph-driven planning state."""
    reader = standards_reader_for_config(config)
    initiate_workflow_task(task, workflow_id, reader)


__all__ = [
    "MAWP_DESIGN",
    "PIPE_WALL_THICKNESS_DESIGN",
    "_SUPPORTED_PLANNING_WORKFLOWS",
    "_finalize_planning_state",
    "bootstrap_new_task",
    "ensure_task_planning",
    "finalize_planning_refresh",
    "maybe_execute_ready_workflow",
    "needs_planning_refresh",
    "resolve_activated_definition_node",
    "refresh_task_planning",
    "standards_reader_for_config",
    "task_ready_for_execution",
]
