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
from engine.reference.graph_edge_schema import workflow_anchor_target
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
from engine.graph.expansion_traversal_trace import record_planning_refresh_trace
from engine.graph.workflow_adapters import apply_workflow_planning_defaults
from engine.planner.planning_structure import (
    build_planning_structure_snapshot,
    structure_unchanged_for_skip,
)
from engine.inspection.operation_tracker import track_operation
from engine.inspection.performance_trace import perf_span


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

    for entry in root.metadata.get("entry_points", []) or []:
        if isinstance(entry, dict) and str(entry.get("role", "")) == "definition_anchor":
            parameter = entry.get("parameter")
            if parameter:
                return str(parameter)
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
            _refresh_task_planning_impl(
                task,
                reader,
                propose_defaults=propose_defaults,
                allow_lightweight_refresh=allow_lightweight_refresh,
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


def _refresh_task_planning_impl(
    task: Task,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
    allow_lightweight_refresh: bool = False,
) -> None:
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if not workflow_id:
        return

    root_slug = normalize_root_id(workflow_id)
    graph = GraphTools(reader)
    engine = GraphEngine()
    uses_micro = engine.uses_micro_graph(reader, root_slug)
    apply_workflow_planning_defaults(task, root_slug)
    existing_inputs = dict(active_facts(task))

    lazy_plan = uses_micro and not engine.expansion_gate_ready(
        root_slug, reader, existing_inputs=existing_inputs
    )
    defaults_added = False
    signature_before_propose: dict[str, Any] | None = None
    stored_signature = task.outputs.get("planning_structure_signature")
    if allow_lightweight_refresh and isinstance(stored_signature, dict):
        signature_before_propose = stored_signature
    with perf_span("graph_preview_eval", "planner"):
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
                lazy_plan = uses_micro and not engine.expansion_gate_ready(
                    root_slug, reader, existing_inputs=existing_inputs
                )
                preview = graph.preview_plan(
                    task_id=task.task_id,
                    root_id=root_slug,
                    inputs=existing_inputs,
                    lazy=lazy_plan,
                )
                defaults_added = True

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
        with perf_span("phased_navigation", "planner"):
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

    record_planning_refresh_trace(
        task.outputs,
        root_id=root_slug,
        preview=preview,
        path_decision=task.outputs.get("path_decision"),
        existing_inputs=existing_inputs,
        lazy=lazy_plan,
        pending_fields=list(
            dict.fromkeys(
                list(assumption_eval.missing_fields)
                + list(expansion_eval.missing_fields)
                + list(missing_inputs)
            )
        ),
    )

    expansion_gate_ready = engine.expansion_gate_ready(
        root_slug,
        reader,
        existing_inputs=dict(active_facts(task)),
    )
    planning_before = planning_projection(task) if allow_lightweight_refresh else {}
    submittable = (
        submittable_parameter_ids(task, planning_before)
        if isinstance(planning_before, dict)
        else []
    )
    snapshot = build_planning_structure_snapshot(
        preview=preview,
        active_nodes=active_nodes,
        phased=phased,
        path_decision=task.outputs.get("path_decision"),
        expansion_eval=expansion_eval,
        assumption_eval=assumption_eval,
        execution_eval=execution_eval,
        missing_inputs=missing_inputs,
        expansion_gate_ready=expansion_gate_ready,
        lazy_plan=lazy_plan,
        submittable_parameters=submittable,
    )
    if (
        defaults_added
        and signature_before_propose is not None
        and snapshot is not None
        and structure_unchanged_for_skip(signature_before_propose, snapshot)
    ):
        defaults_added = False
    stored_signature = task.outputs.get("planning_structure_signature")
    skip_goal_tree = (
        allow_lightweight_refresh
        and not defaults_added
        and snapshot is not None
        and isinstance(stored_signature, dict)
        and structure_unchanged_for_skip(stored_signature, snapshot)
    )

    if skip_goal_tree:
        with perf_span("planning_refresh_skipped", "planner", notes="structure_unchanged"):
            pass
    else:
        refresh_goal_tree(
            task,
            reader,
            preview=preview,
            question_map=question_map,
            phased=phased,
            root_slug=root_slug,
        )

    if snapshot is not None:
        task.outputs["planning_structure_signature"] = snapshot

    _finalize_planning_state(
        task,
        reader,
        workflow_id=workflow_id,
        root_slug=root_slug,
        preview=preview,
        graph=graph,
        engine=engine,
        active_nodes=active_nodes,
        uses_micro=uses_micro,
    )


def _graph_navigation_snapshot(task: Task) -> dict[str, Any] | None:
    nav = task.outputs.get("graph_navigation")
    return nav if isinstance(nav, dict) else None


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
    if workflow not in _SUPPORTED_PLANNING_WORKFLOWS:
        return False

    nav = _graph_navigation_snapshot(task)
    nav_phase = str((nav or {}).get("current_phase") or "")

    if (
        workflow == PIPE_WALL_THICKNESS_DESIGN
        and nav_phase == NavigationPhase.DEFINITION_EQUATION_COMPLETION.value
    ):
        thickness_ready = (
            task.outputs.get("t") is not None
            or task.outputs.get("required_thickness") is not None
            or has_execution_trace(task)
        )
        if thickness_ready:
            return False

    planning = planning_projection(task)
    if workflow == PIPE_WALL_THICKNESS_DESIGN and _pipe_wall_ready_for_primary_execution(
        task, planning
    ):
        return True

    if nav_phase == NavigationPhase.READY.value and not has_execution_trace(task):
        from engine.planner.graph_navigation import graph_navigation_has_collectable_missing

        ready = not graph_navigation_has_collectable_missing(nav)
        return ready

    roots = task.goal_store.roots()
    if roots and not task.goal_store.children(roots[0].id):
        return False

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
    apply_workflow_planning_defaults(task, workflow_id)
    refresh_task_planning(task, reader)
