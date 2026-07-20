"""Engine-owned workflow initiation and planning refresh orchestration."""

from __future__ import annotations

from typing import Any

from engine.graph.expansion_policy import collect_workflow_expansion_fields
from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id
from engine.graph.workflow_adapters import apply_workflow_planning_defaults
from engine.inspection.operation_tracker import track_operation
from engine.inspection.performance_trace import perf_span
from engine.navigation.timeline_sync import sync_timeline_input_order
from engine.planning.definition_anchor import resolve_activated_definition_node
from engine.planning.planning_refresh import (
    PlanningRefreshFinalizeContext,
    refresh_task_planning_state,
)
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.router import is_supported_planning_workflow
from engine.state.decision_recorder import migrate_path_decision_to_context
from engine.state.execution_context_sync import refresh_execution_context_for_task
from engine.state.goal_projection import planning_projection
from engine.state.goal_satisfaction import refresh_goal_satisfaction
from engine.state.task_facts import active_facts, store_proposed_default
from models.task import Task, TaskStatus


def _seed_expansion_gate_defaults(
    task: Task,
    reader: StandardsReader,
    workflow_id: str,
) -> None:
    """Seed graph-authored expansion-gate defaults before the first replan."""
    root_slug = normalize_root_id(workflow_id)
    resolved = resolve_workflow_node_id(root_slug)
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    if micro is None:
        return
    store = micro.store
    graph_root = store.resolve_node_id(resolved) or resolved
    gate_fields = collect_workflow_expansion_fields(store, graph_root)
    if not gate_fields:
        return

    anchor = resolve_activated_definition_node(reader, workflow_id)
    graph = GraphTools(reader)
    existing = dict(active_facts(task))
    for field_id in sorted(gate_fields):
        if task.fact_store.active_fact(field_id) is not None:
            continue
        from engine.graph.assumption_checker import field_value

        if field_value(field_id, existing) is not None:
            continue
        proposed = graph.resolve_and_propose_path_inputs(
            root_slug,
            existing_inputs=existing,
            task_id=task.task_id,
        )
        fact = proposed.get(field_id)
        if fact is not None:
            from engine.state.task_facts import store_fact

            store_fact(task, fact)
            existing = dict(active_facts(task))
            continue
        if field_id.endswith("_section"):
            store_proposed_default(
                task,
                field_id,
                True,
                unit="dimensionless",
                introduced_at_node=anchor,
            )
            existing = dict(active_facts(task))


def finalize_planning_refresh(
    task: Task,
    reader: StandardsReader,
    ctx: PlanningRefreshFinalizeContext,
) -> None:
    """Apply post-refresh side effects shared by API and engine callers."""
    from engine.graph.definition_equations import (
        has_execution_trace,
        pending_definition_equation_inputs,
        try_complete_definition_equations,
    )
    from engine.planner.workflow_goal_metadata import goal_output_value_for_task
    from engine.resolution.goal_resolver import resolve_ready_goals

    with perf_span("resolve_ready_goals", "planner"):
        if resolve_ready_goals(task, reader.standards_root):
            refresh_goal_satisfaction(task)

    task.active_nodes = ctx.active_nodes

    _apply_post_execution_definition_planning(
        task,
        reader,
        execution_order=ctx.preview.execution_order,
        graph=ctx.graph,
        root_slug=ctx.root_slug,
        plan=ctx.preview,
    )
    refresh_goal_satisfaction(task)

    migrate_path_decision_to_context(task)
    refresh_execution_context_for_task(task, workflow_id=ctx.workflow_id, reader=reader)

    planning = planning_projection(task)
    sync_timeline_input_order(task, planning, reader=reader)

    if ctx.uses_micro:
        ctx.engine.prefetch(
            reader,
            task_id=task.task_id,
            root_id=ctx.root_slug,
            inputs=dict(active_facts(task)),
            horizon=1,
        )


def _apply_post_execution_definition_planning(
    task: Task,
    reader: StandardsReader,
    *,
    execution_order: tuple[str, ...] | list[str],
    graph: GraphTools,
    root_slug: str,
    plan: Any,
) -> None:
    from engine.graph.definition_equations import (
        has_execution_trace,
        pending_definition_equation_inputs,
        try_complete_definition_equations,
    )
    from engine.planner.workflow_goal_metadata import goal_output_value_for_task
    from engine.state.task_facts import store_fact

    if not has_execution_trace(task):
        return

    pending = pending_definition_equation_inputs(task, reader, execution_order)
    if not pending:
        if goal_output_value_for_task(task) is not None:
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


def refresh_workflow_planning(
    task: Task,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
    allow_lightweight_refresh: bool = True,
) -> None:
    """Recompute graph-derived planning state and finalize task projections."""
    with track_operation(
        "refresh_workflow_planning",
        category="planning",
        task_id=task.task_id,
        propose_defaults=propose_defaults,
    ):
        with perf_span(
            "refresh_workflow_planning",
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


def initiate_workflow_task(
    task: Task,
    workflow_id: str,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
) -> None:
    """Initialize a task for a workflow — canonical initiation for all runtimes."""
    with track_operation(
        "initiate_workflow_task",
        category="bootstrap",
        task_id=task.task_id,
        workflow_id=workflow_id,
    ):
        task.outputs["workflow"] = workflow_id
        task.outputs["selected_root"] = workflow_id

        if not is_supported_planning_workflow(workflow_id):
            from engine.planner.goal_builder import build_goal_tree

            build_goal_tree(task, reader)
            return

        _seed_expansion_gate_defaults(task, reader, workflow_id)
        apply_workflow_planning_defaults(task, workflow_id)
        refresh_workflow_planning(task, reader, propose_defaults=propose_defaults)
