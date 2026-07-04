"""Bootstrap and refresh desktop task planning state from the graph engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config.loader import CLIConfig
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
from engine.graph.workflow_navigation import load_workflow_navigation
from engine.planner.planner import _INPUT_QUESTIONS
from engine.planner.tools import GraphTools
from engine.reference.graph_edge_schema import edge_target, iter_stored_edges
from engine.reference.standards_reader import StandardsReader
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.state.task_facts import active_facts, store_fact, store_user_fact
from engine.planner.goal_builder import refresh_goal_tree
from engine.state.goal_projection import planning_projection
from engine.state.decision_recorder import migrate_path_decision_to_context
from engine.state.execution_context_sync import refresh_execution_context_for_task
from models.agent import AgentAction
from models.fact import Fact, fact_scalar_value
from models.planning import NavigationPhase
from models.task import Task, TaskStatus
from api.material_catalog_service import warm_material_catalog
from api.workflow_timeline import is_mawp_task, submittable_parameter_ids
from engine.executor.mawp_geometry_resolver import apply_geometry_input_mode_default


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
        "material",
        "design_temperature",
        "nominal_pipe_size",
        "outside_diameter",
        "pipe_schedule",
        "actual_wall_thickness",
        "geometry_input_mode",
        "joint_category",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
        "corrosion_allowance",
    }
)

_SUPPORTED_PLANNING_WORKFLOWS = frozenset({PIPE_WALL_THICKNESS_DESIGN, MAWP_DESIGN})


def refresh_task_planning(
    task: Task,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
) -> None:
    """Recompute goal tree and active_nodes from current task inputs."""
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if not workflow_id:
        return

    root_slug = normalize_root_id(workflow_id)
    graph = GraphTools(reader)
    engine = GraphEngine()
    uses_micro = engine.uses_micro_graph(reader, root_slug)
    if root_slug == MAWP_DESIGN:
        apply_geometry_input_mode_default(task)
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

    question_map: dict[str, str] = dict(_INPUT_QUESTIONS)
    if uses_micro:
        for field_id in (
            assumption_eval.missing_fields
            + expansion_eval.missing_fields
            + execution_eval.missing_fields
            + missing_inputs
        ):
            graph_q = graph_question_for_field(reader, field_id)
            if graph_q:
                question_map[field_id] = graph_q
    for field_id, question in assumption_eval.field_questions.items():
        question_map.setdefault(field_id, question)
    for field_id, question in expansion_eval.field_questions.items():
        question_map.setdefault(field_id, question)
    for field_id, question in execution_eval.field_questions.items():
        question_map.setdefault(field_id, question)

    nav_config = load_workflow_navigation(reader, root_slug)
    phased = build_workflow_phased_navigation(
        config=nav_config,
        assumption_eval=assumption_eval,
        expansion_eval=expansion_eval,
        user_inputs=missing_inputs,
        execution_eval=execution_eval,
        question_map=question_map,
    )

    assumption_gate_fields = nav_config.assumption_gate_fields
    missing_assumptions = [
        field_id
        for field_id in assumption_eval.missing_fields + expansion_eval.missing_fields
        if field_id in assumption_gate_fields
    ]
    missing_execution = [
        field_id
        for field_id in list(expansion_eval.missing_fields) + list(execution_eval.missing_fields)
        if field_id not in assumption_gate_fields
    ]

    definition_node = resolve_activated_definition_node(
        reader,
        workflow_id,
        execution_order=preview.execution_order,
    )
    active_nodes = list(task.active_nodes)
    if definition_node and definition_node not in active_nodes:
        active_nodes.insert(0, definition_node)
    elif definition_node:
        active_nodes = [definition_node] + [node for node in active_nodes if node != definition_node]

    task.outputs["active_definition_node"] = definition_node
    task.outputs["path_decision"] = _path_decision(existing_inputs, exec_nodes)
    task.outputs["phase_allowed_fields"] = nav_config.phase_allowlists()
    task.outputs["selected_nodes"] = exec_nodes
    if uses_micro:
        task.outputs["graph_input_order"] = list(graph_input_step_order(reader, preview))
        task.outputs["graph_step_titles"] = graph_step_titles(reader, preview)

    refresh_goal_tree(
        task,
        reader,
        preview=preview,
        question_map=question_map,
        phased=phased,
        root_slug=root_slug,
    )
    task.active_nodes = active_nodes

    _apply_post_execution_definition_planning(
        task,
        reader,
        execution_order=preview.execution_order,
        graph=graph,
        root_slug=root_slug,
        plan=preview,
    )

    migrate_path_decision_to_context(task)
    refresh_execution_context_for_task(task, workflow_id=workflow_id, reader=reader)

    planning = planning_projection(task)
    if "material" in submittable_parameter_ids(task, planning):
        warm_material_catalog(reader.standards_root)

    if uses_micro:
        engine.prefetch(
            reader,
            task_id=task.task_id,
            root_id=root_slug,
            inputs=dict(active_facts(task)),
            horizon=1,
        )


def task_ready_for_execution(task: Task) -> bool:
    if task.status in {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}:
        return False
    workflow = str(task.outputs.get("workflow") or "")
    if workflow not in _SUPPORTED_PLANNING_WORKFLOWS:
        return False

    planning = planning_projection(task)

    if (
        workflow == PIPE_WALL_THICKNESS_DESIGN
        and planning.get("current_phase") == NavigationPhase.DEFINITION_EQUATION_COMPLETION.value
    ):
        return False

    if planning.get("current_phase") == NavigationPhase.READY.value:
        return True

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
    if not pending and has_execution_trace(task):
        if task.outputs.get("required_thickness") is not None and task.outputs.get("minimum_required_thickness") is None:
            if "corrosion_allowance" not in active_facts(task):
                pending = ["corrosion_allowance"]
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

    from engine.state.task_goals import expand_goal
    from models.goal import input_goal

    phase_key = NavigationPhase.DEFINITION_EQUATION_COMPLETION.value
    roots = task.goal_store.roots()
    root_id = roots[0].id if roots else None
    for input_id in pending:
        if root_id and not any(g.key == f"input-{input_id}" for g in task.goal_store.goals.values()):
            child = input_goal(
                key=f"input-{input_id}",
                name=f"Provide {input_id.replace('_', ' ')}",
                target_parameter=input_id,
                task_id=task.task_id,
                prompt=f"Provide {input_id.replace('_', ' ')}",
                workflow_id=str(task.outputs.get("workflow") or ""),
                parent_goal=root_id,
                phase=phase_key,
            )
            expand_goal(task, root_id, child)

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
    task.outputs["workflow"] = workflow_id
    task.outputs["selected_root"] = workflow_id

    if workflow_id not in _SUPPORTED_PLANNING_WORKFLOWS:
        from engine.planner.goal_builder import build_goal_tree

        reader = standards_reader_for_config(config)
        build_goal_tree(task, reader)
        return

    reader = standards_reader_for_config(config)
    _apply_default_expansion_assumptions(task)
    if workflow_id == MAWP_DESIGN:
        apply_geometry_input_mode_default(task)
    refresh_task_planning(task, reader)


def _apply_default_expansion_assumptions(task: Task) -> None:
    """Straight-pipe scope is confirmed at task selection; assume true when the task opens."""
    if task.fact_store.active_fact("straight_pipe_section") is not None:
        return
    store_user_fact(
        task,
        "straight_pipe_section",
        True,
        unit="dimensionless",
    )


def _path_decision(
    inputs: dict[str, Fact],
    exec_nodes: list[str],
) -> dict[str, Any] | None:
    loading = inputs.get("pressure_loading")
    value = fact_scalar_value(loading) if loading is not None else None
    if value == "internal_pressure" and "304.1.2-a" in exec_nodes:
        return {"pressure_loading": "internal_pressure", "selected_node": "304.1.2-a"}
    if value == "external_pressure" and "B313-304.1.3" in exec_nodes:
        return {"pressure_loading": "external_pressure", "selected_node": "B313-304.1.3"}
    if "B313-MAWP-CALCULATION" in exec_nodes:
        return {"selected_node": "B313-MAWP-CALCULATION"}
    return None
