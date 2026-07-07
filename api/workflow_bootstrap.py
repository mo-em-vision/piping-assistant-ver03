"""Bootstrap and refresh desktop task planning state from the graph engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.parameter_keys import MATERIAL_GRADE_KEY
from engine.executor.coefficient_lookup import apply_coefficient_lookups
from engine.executor.executor import execute_workflow
from engine.graph.definition_equations import (
    has_execution_trace,
    pending_definition_equation_inputs,
    try_complete_definition_equations,
)
from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id
from engine.graph.graph_timeline import graph_input_step_order, graph_question_for_field, graph_step_titles
from engine.graph.navigation_phases import build_workflow_phased_navigation
from engine.graph.path_decision import resolve_path_decision
from engine.graph.workflow_navigation import load_workflow_navigation, workflow_collection_field_order
from engine.messaging.parameter_input_prompt import build_parameter_input_prompt
from engine.planner.tools import GraphTools
from engine.reference.graph_edge_schema import edge_target, iter_stored_edges, workflow_anchor_target
from engine.reference.standards_reader import StandardsReader
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.state.task_facts import active_facts, store_fact, store_proposed_default
from engine.planner.goal_builder import refresh_goal_tree
from engine.state.goal_projection import planning_projection
from engine.state.decision_recorder import migrate_path_decision_to_context
from engine.state.execution_context_sync import refresh_execution_context_for_task
from models.agent import AgentAction
from models.fact import Fact, fact_scalar_value
from models.planning import NavigationPhase
from models.task import Task, TaskStatus
from api.material_catalog_service import warm_material_catalog
from api.workflow_timeline import is_mawp_task, submittable_parameter_ids, sync_timeline_input_order
from engine.executor.mawp_geometry_resolver import (
    apply_geometry_input_mode_default,
    apply_mawp_pressure_loading_default,
    apply_wall_thickness_basis_from_geometry,
)
from engine.inspection.operation_tracker import track_operation


def standards_reader_for_config(config: CLIConfig) -> StandardsReader:
    return StandardsReader(config.standards_root, standard="asme_b31.3")


def resolve_activated_definition_node(
    reader: StandardsReader,
    workflow_id: str,
    *,
    execution_order: tuple[str, ...] | list[str] | None = None,
) -> str | None:
    """Return the workflow's primary definition/section node."""
    slug = normalize_root_id(workflow_id)
    resolved_slug = resolve_workflow_node_id(slug)
    engine = GraphEngine()
    if engine.uses_micro_graph(reader, resolved_slug):
        store = engine._micro_engine(reader)
        if store is not None:
            resolved = engine._resolve_micro_root(resolved_slug, reader)
            wf = store.store.get_node(resolved)
            if wf is not None:
                anchor = workflow_anchor_target(wf.metadata)
                if isinstance(anchor, str):
                    return anchor
                anchors = wf.metadata.get("anchors_to")
                if isinstance(anchors, str):
                    return anchors
    try:
        root = reader.load(slug)
    except FileNotFoundError:
        return None

    for item in iter_stored_edges(root.metadata):
        if str(item.get("type", "")) == "starts_from_paragraph":
            target = edge_target(item)
            if target:
                return target

    for entry in root.metadata.get("entry_points", []) or []:
        if isinstance(entry, dict) and str(entry.get("role", "")) == "definition_anchor":
            paragraph = entry.get("paragraph")
            if paragraph:
                return str(paragraph)

    anchor = workflow_anchor_target(root.metadata)
    if isinstance(anchor, str):
        return anchor

    for item in root.metadata.get("depends_on", []) or []:
        if not isinstance(item, dict):
            continue
        node_id = item.get("node_id")
        if not node_id:
            continue
        try:
            record = reader.load(str(node_id))
        except FileNotFoundError:
            continue
        if str(record.metadata.get("type", "")) in {"definition", "paragraph"}:
            return str(node_id)

    order = execution_order
    if order is None:
        graph = GraphTools(reader)
        order = graph.preview_plan(
            task_id="bootstrap",
            root_id=resolved_slug,
            inputs={},
        ).execution_order

    for node_id in order:
        try:
            record = reader.load(node_id)
        except FileNotFoundError:
            continue
        if str(record.metadata.get("type", "")) in {"definition", "paragraph"}:
            return node_id
    return None


_PROPOSE_DEFAULTS_ON_FIELDS = frozenset(
    {
        "material_grade",
        "design_temperature",
        "nominal_pipe_size",
        "outside_diameter",
        "pipe_schedule",
        "actual_wall_thickness",
        "geometry_input_mode",
        "joint_category",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "corrosion_allowance",
    }
)

_SUPPORTED_PLANNING_WORKFLOWS = frozenset({PIPE_WALL_THICKNESS_DESIGN, MAWP_DESIGN})


def _sync_active_nodes(
    task: Task,
    *,
    definition_node: str | None,
    execution_order: tuple[str, ...] | list[str],
) -> list[str]:
    """Keep active_nodes aligned with the definition anchor and current graph preview."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add(node_id: str | None) -> None:
        if node_id and node_id not in seen:
            seen.add(node_id)
            ordered.append(node_id)

    add(definition_node)
    for node_id in execution_order:
        add(node_id)
    for node_id in task.active_nodes:
        add(node_id)
    return ordered


def needs_planning_refresh(task: Task) -> bool:
    """Return True when a supported workflow task should rebuild its goal tree."""
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if workflow_id not in _SUPPORTED_PLANNING_WORKFLOWS:
        return False
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
) -> None:
    """Recompute goal tree and active_nodes from current task inputs."""
    with track_operation(
        "refresh_task_planning",
        category="planning",
        task_id=task.task_id,
        propose_defaults=propose_defaults,
    ):
        _refresh_task_planning_impl(task, reader, propose_defaults=propose_defaults)


def _refresh_task_planning_impl(
    task: Task,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
) -> None:
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if not workflow_id:
        return

    root_slug = normalize_root_id(workflow_id)
    graph = GraphTools(reader)
    engine = GraphEngine()
    uses_micro = engine.uses_micro_graph(reader, root_slug)
    if root_slug == MAWP_DESIGN:
        apply_geometry_input_mode_default(task)
        apply_mawp_pressure_loading_default(task)
        apply_wall_thickness_basis_from_geometry(task)
    existing_inputs = dict(active_facts(task))

    lazy_plan = uses_micro and not engine.expansion_gate_ready(
        root_slug, reader, existing_inputs=existing_inputs
    )
    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id=root_slug,
        inputs=existing_inputs,
        lazy=lazy_plan,
    )
    if propose_defaults:
        added = _apply_proposed_path_inputs(task, graph, root_slug, plan=preview)
        if added:
            existing_inputs = dict(active_facts(task))
            preview = graph.preview_plan(
                task_id=task.task_id,
                root_id=root_slug,
                inputs=existing_inputs,
            )

    apply_coefficient_lookups(task, reader.standards_root)
    existing_inputs = dict(active_facts(task))

    exec_nodes = _execution_nodes(reader, preview.execution_order)

    assumption_eval = graph.evaluate_assumptions(
        root_slug,
        existing_inputs=existing_inputs,
        plan=preview,
    )
    expansion_eval = graph.evaluate_expansion_interactions(
        root_slug,
        existing_inputs=existing_inputs,
        plan=preview,
    )
    missing_inputs = graph.required_user_inputs(
        root_slug,
        existing_inputs=set(existing_inputs.keys()),
        task_inputs=existing_inputs,
        plan=preview,
    )
    execution_eval = graph.evaluate_execution_assumptions(
        root_slug,
        existing_inputs=existing_inputs,
        plan=preview,
    )
    if has_execution_trace(task):
        for input_id in pending_definition_equation_inputs(
            task,
            reader,
            preview.execution_order,
        ):
            if input_id not in execution_eval.missing_fields:
                execution_eval.missing_fields.append(input_id)

    question_map: dict[str, str] = {}
    field_ids = list(
        dict.fromkeys(
            list(assumption_eval.missing_fields)
            + list(expansion_eval.missing_fields)
            + list(execution_eval.missing_fields)
            + list(missing_inputs)
        )
    )
    for field_id in field_ids:
        prompt = build_parameter_input_prompt(reader, task, field_id)
        if prompt:
            question_map[field_id] = prompt
    for eval_obj in (expansion_eval, assumption_eval, execution_eval):
        for field_id, question in eval_obj.field_questions.items():
            question_map.setdefault(field_id, question)
    if uses_micro:
        for field_id in field_ids:
            graph_q = graph_question_for_field(reader, field_id)
            if graph_q:
                question_map.setdefault(field_id, graph_q)

    nav_config = load_workflow_navigation(reader, root_slug)
    phased = build_workflow_phased_navigation(
        config=nav_config,
        assumption_eval=assumption_eval,
        expansion_eval=expansion_eval,
        user_inputs=missing_inputs,
        execution_eval=execution_eval,
        question_map=question_map,
        existing_inputs=existing_inputs,
        post_thickness_outputs=dict(task.outputs),
        has_execution=has_execution_trace(task),
    )

    definition_node = resolve_activated_definition_node(
        reader,
        workflow_id,
        execution_order=preview.execution_order,
    )
    active_nodes = _sync_active_nodes(
        task,
        definition_node=definition_node,
        execution_order=preview.execution_order,
    )

    task.outputs["active_definition_node"] = definition_node
    task.outputs["phase_allowed_fields"] = nav_config.phase_allowlists()
    task.outputs["selected_nodes"] = exec_nodes
    if uses_micro:
        task.outputs["graph_input_order"] = list(graph_input_step_order(reader, preview))
        task.outputs["graph_step_titles"] = graph_step_titles(reader, preview)
        task.outputs["collection_field_order"] = list(
            workflow_collection_field_order(reader, root_slug)
        )

    micro = engine._micro_engine(reader)
    graph_store = micro.store if micro is not None else None
    task.outputs["path_decision"] = resolve_path_decision(
        graph_store,
        exec_nodes,
        existing_inputs,
    )
    refresh_goal_tree(
        task,
        reader,
        preview=preview,
        question_map=question_map,
        phased=phased,
        root_slug=root_slug,
    )

    from engine.resolution.goal_resolver import resolve_ready_goals
    from engine.state.goal_satisfaction import refresh_goal_satisfaction

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


def _graph_navigation_snapshot(task: Task) -> dict[str, Any] | None:
    nav = task.outputs.get("graph_navigation")
    return nav if isinstance(nav, dict) else None


def task_ready_for_execution(task: Task) -> bool:
    if task.status in {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}:
        return False
    workflow = str(task.outputs.get("workflow") or "")
    if workflow not in _SUPPORTED_PLANNING_WORKFLOWS:
        return False

    nav = _graph_navigation_snapshot(task)
    nav_phase = str((nav or {}).get("current_phase") or "")

    if (
        workflow == PIPE_WALL_THICKNESS_DESIGN
        and nav_phase == NavigationPhase.DEFINITION_EQUATION_COMPLETION.value
    ):
        return False

    if nav_phase == NavigationPhase.READY.value and not has_execution_trace(task):
        from engine.planner.graph_navigation import graph_navigation_has_collectable_missing

        ready = not graph_navigation_has_collectable_missing(nav)
        # #region agent log
        from api.debug_trace import agent_debug_log

        agent_debug_log(
            "workflow_bootstrap.py:task_ready_for_execution",
            "graph navigation ready gate",
            {
                "task_id": task.task_id,
                "ready": ready,
                "goal_keys": [g.key for g in task.goal_store.goals.values()],
                "nav_phase": nav_phase,
                "missing_inputs": (nav or {}).get("missing_inputs"),
            },
            hypothesis_id="A",
            run_id="post-fix",
        )
        # #endregion
        return ready

    roots = task.goal_store.roots()
    if roots and not task.goal_store.children(roots[0].id):
        return False

    planning = planning_projection(task)

    if planning.get("action") != AgentAction.PROPOSE_PATH.value:
        return False

    return not any(
        planning.get(key)
        for key in ("missing_inputs", "missing_assumptions", "missing_execution_assumptions")
    )


def maybe_execute_ready_workflow(
    task_id: str,
    manager: TaskStateManager,
    reader: StandardsReader,
) -> Task:
    """Run the engineering executor when phased navigation has collected all required inputs."""
    with track_operation("maybe_execute_ready_workflow", category="execution", task_id=task_id):
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
    # #region agent log
    from api.debug_trace import agent_debug_log

    agent_debug_log(
        "workflow_bootstrap.py:maybe_execute_ready_workflow",
        "post execute snapshot",
        {
            "task_id": task_id,
            "has_t": task.outputs.get("t") is not None
            or task.outputs.get("required_thickness") is not None,
            "has_trace": has_execution_trace(task),
            "validation_status": (
                (task.outputs.get("_validation_trace") or [{}])[-1].get("status")
                if isinstance(task.outputs.get("_validation_trace"), list)
                and task.outputs.get("_validation_trace")
                else None
            ),
        },
        hypothesis_id="F",
        run_id="post-fix",
    )
    # #endregion
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


def _apply_proposed_path_inputs(
    task: Task,
    graph: GraphTools,
    root_slug: str,
    *,
    plan: Any | None = None,
) -> bool:
    proposed = graph.resolve_and_propose_path_inputs(
        root_slug,
        existing_inputs=dict(active_facts(task)),
        plan=plan,
        task_id=task.task_id,
    )
    added = False
    for input_id, fact in proposed.items():
        if input_id not in active_facts(task):
            store_fact(task, fact)
            added = True
    return added


def _execution_nodes(reader: StandardsReader, execution_order: tuple[str, ...] | list[str]) -> list[str]:
    executable_types = {"calculation", "lookup", "equation"}
    nodes: list[str] = []
    for node_id in execution_order:
        node_type = str(reader.load(node_id).metadata.get("type", ""))
        if node_type in executable_types:
            nodes.append(node_id)
        elif node_type not in {"root", "workflow", "standard_section", "text", "parameter", "assumption", "interaction", "table", "definition"}:
            nodes.append(node_id)
    return nodes


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

    if workflow_id not in _SUPPORTED_PLANNING_WORKFLOWS:
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
    if workflow_id == MAWP_DESIGN:
        apply_geometry_input_mode_default(task)
        apply_mawp_pressure_loading_default(task)
        apply_wall_thickness_basis_from_geometry(task)
    refresh_task_planning(task, reader)
