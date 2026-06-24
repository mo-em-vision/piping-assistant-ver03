"""Bootstrap and refresh desktop task planning state from the graph engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config.loader import CLIConfig
from engine.executor.coefficient_lookup import apply_coefficient_lookups
from engine.executor.executor import execute_workflow
from engine.graph.graph_engine import normalize_root_id
from engine.graph.navigation_phases import build_phased_navigation
from engine.planner.planner import _INPUT_QUESTIONS
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.agent import AgentAction
from models.input import EngineeringInput, InputSource, InputStatus
from models.planning import NavigationPhase
from models.task import Task, TaskStatus
from api.material_catalog_service import warm_material_catalog
from api.workflow_timeline import submittable_parameter_ids


def standards_reader_for_config(config: CLIConfig) -> StandardsReader:
    return StandardsReader(config.standards_root, standard="asme_b31.3")


def resolve_activated_definition_node(
    reader: StandardsReader,
    workflow_id: str,
    *,
    execution_order: tuple[str, ...] | list[str] | None = None,
) -> str | None:
    """Return the workflow's primary definition node, when declared on the root."""
    slug = normalize_root_id(workflow_id)
    try:
        root = reader.load(slug)
    except FileNotFoundError:
        return None

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
        if str(record.metadata.get("type", "")) == "definition":
            return str(node_id)

    order = execution_order
    if order is None:
        graph = GraphTools(reader)
        order = graph.preview_plan(task_id="bootstrap", root_id=slug, inputs={}).execution_order

    for node_id in order:
        try:
            record = reader.load(node_id)
        except FileNotFoundError:
            continue
        if str(record.metadata.get("type", "")) == "definition":
            return node_id
    return None


_PROPOSE_DEFAULTS_ON_FIELDS = frozenset(
    {
        "material",
        "design_temperature",
        "nominal_pipe_size",
        "outside_diameter",
        "joint_category",
        "weld_joint_efficiency",
        "weld_strength_reduction",
        "temperature_coefficient",
        "corrosion_allowance",
    }
)


def refresh_task_planning(
    task: Task,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
) -> None:
    """Recompute planning_summary and active_nodes from current task inputs."""
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if not workflow_id:
        return

    root_slug = normalize_root_id(workflow_id)
    graph = GraphTools(reader)
    existing_inputs = dict(task.inputs)

    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id=root_slug,
        inputs=existing_inputs,
    )
    if propose_defaults:
        added = _apply_proposed_path_inputs(task, graph, root_slug, plan=preview)
        if added:
            existing_inputs = dict(task.inputs)
            preview = graph.preview_plan(
                task_id=task.task_id,
                root_id=root_slug,
                inputs=existing_inputs,
            )

    apply_coefficient_lookups(task, reader.standards_root)
    existing_inputs = dict(task.inputs)

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
    for field_id, question in assumption_eval.field_questions.items():
        question_map.setdefault(field_id, question)
    for field_id, question in expansion_eval.field_questions.items():
        question_map.setdefault(field_id, question)
    for field_id, question in execution_eval.field_questions.items():
        question_map.setdefault(field_id, question)

    phased = build_phased_navigation(
        assumption_eval=assumption_eval,
        expansion_eval=expansion_eval,
        user_inputs=missing_inputs,
        execution_eval=execution_eval,
        question_map=question_map,
    )

    missing_assumptions = [
        field_id
        for field_id in assumption_eval.missing_fields + expansion_eval.missing_fields
        if field_id in {"straight_pipe_section", "pressure_loading"}
    ]
    missing_execution = [
        field_id
        for field_id in list(expansion_eval.missing_fields) + list(execution_eval.missing_fields)
        if field_id not in {"straight_pipe_section", "pressure_loading"}
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

    try:
        root_record = reader.load(root_slug)
        goal = str(root_record.metadata.get("title") or root_record.metadata.get("purpose") or workflow_id)
    except FileNotFoundError:
        goal = workflow_id.replace("_", " ")

    action = AgentAction.REQUEST_INPUT if phased.all_missing else AgentAction.PROPOSE_PATH
    if phased.blocked_nodes:
        action = AgentAction.CLARIFY

    task.outputs["planning_summary"] = {
        "goal": goal,
        "intent": workflow_id,
        "selected_root": root_slug,
        "selected_nodes": exec_nodes,
        "active_definition_node": definition_node,
        "missing_assumptions": missing_assumptions,
        "missing_execution_assumptions": missing_execution,
        "missing_inputs": missing_inputs,
        "current_phase": phased.current_phase.value,
        "phase_missing": phased.phase_missing,
        "phase_questions": phased.phase_questions,
        "path_decision": _path_decision(existing_inputs, exec_nodes),
        "confidence": 1.0,
        "action": action.value,
    }
    task.active_nodes = active_nodes

    planning_summary = task.outputs.get("planning_summary")
    if isinstance(planning_summary, dict) and "material" in submittable_parameter_ids(
        task, planning_summary
    ):
        warm_material_catalog(reader.standards_root)


def task_ready_for_execution(task: Task) -> bool:
    if task.status in {TaskStatus.COMPLETED, TaskStatus.INVALIDATED}:
        return False
    if str(task.outputs.get("workflow") or "") != PIPE_WALL_THICKNESS_DESIGN:
        return False

    planning = task.outputs.get("planning_summary") or {}
    if not isinstance(planning, dict):
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
    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task_id, task)
    return task


def _apply_proposed_path_inputs(
    task: Task,
    graph: GraphTools,
    root_slug: str,
    *,
    plan: Any | None = None,
) -> bool:
    proposed = graph.resolve_and_propose_path_inputs(
        root_slug,
        existing_inputs=dict(task.inputs),
        plan=plan,
    )
    added = False
    for input_id, engineering_input in proposed.items():
        if input_id not in task.inputs:
            task.inputs[input_id] = engineering_input
            added = True
    return added


def _execution_nodes(reader: StandardsReader, execution_order: tuple[str, ...] | list[str]) -> list[str]:
    nodes: list[str] = []
    for node_id in execution_order:
        node_type = str(reader.load(node_id).metadata.get("type", ""))
        if node_type != "root":
            nodes.append(node_id)
    return nodes


def bootstrap_new_task(task: Task, workflow_id: str, config: CLIConfig) -> None:
    """Initialize a newly created task with graph-driven planning state."""
    task.outputs["workflow"] = workflow_id
    task.outputs["selected_root"] = workflow_id

    if workflow_id != PIPE_WALL_THICKNESS_DESIGN:
        task.outputs["planning_summary"] = {
            "goal": workflow_id.replace("_", " "),
            "intent": workflow_id,
            "selected_root": workflow_id,
            "selected_nodes": [],
            "missing_assumptions": [],
            "missing_execution_assumptions": [],
            "missing_inputs": [],
            "current_phase": NavigationPhase.READY.value,
            "phase_missing": {},
            "phase_questions": {},
            "path_decision": None,
            "confidence": 1.0,
            "action": AgentAction.REQUEST_INPUT.value,
        }
        return

    reader = standards_reader_for_config(config)
    _apply_default_expansion_assumptions(task)
    refresh_task_planning(task, reader)


def _apply_default_expansion_assumptions(task: Task) -> None:
    """Straight-pipe scope is confirmed at task selection; assume true when the task opens."""
    if task.inputs.get("straight_pipe_section") is not None:
        return
    task.inputs["straight_pipe_section"] = EngineeringInput(
        input_id="straight_pipe_section",
        value=True,
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
        default=True,
        requires_confirmation=False,
    )


def _path_decision(
    inputs: dict[str, Any],
    exec_nodes: list[str],
) -> dict[str, Any] | None:
    loading = inputs.get("pressure_loading")
    value = getattr(loading, "value", None) if loading is not None else None
    if value == "internal_pressure" and "B313-304.1.2" in exec_nodes:
        return {"pressure_loading": "internal_pressure", "selected_node": "B313-304.1.2"}
    if value == "external_pressure" and "B313-304.1.3" in exec_nodes:
        return {"pressure_loading": "external_pressure", "selected_node": "B313-304.1.3"}
    return None
