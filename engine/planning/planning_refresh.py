"""Engine-owned planning refresh orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.executor.coefficient_lookup import apply_coefficient_lookups
from engine.graph.definition_equations import (
    has_execution_trace,
    pending_definition_equation_inputs,
)
from engine.graph.expansion_traversal_trace import record_planning_refresh_trace
from engine.graph.graph_engine import GraphEngine, normalize_root_id
from engine.graph.graph_timeline import graph_input_step_order, graph_question_for_field, graph_step_titles
from engine.graph.navigation_phases import build_workflow_phased_navigation
from engine.graph.path_decision import resolve_path_decision
from engine.graph.workflow_adapters import apply_workflow_planning_defaults
from engine.graph.workflow_navigation import load_workflow_navigation, workflow_collection_field_order
from engine.inspection.performance_trace import perf_span
from engine.messaging.parameter_input_prompt import build_parameter_input_prompt
from engine.planning.definition_anchor import resolve_activated_definition_node
from engine.planner.goal_builder import refresh_goal_tree
from engine.planner.planning_structure import (
    build_planning_structure_snapshot,
    structure_unchanged_for_skip,
)
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.state.task_facts import active_facts, store_fact
from models.task import Task


@dataclass(frozen=True)
class PlanningRefreshFinalizeContext:
    """Values required by API finalization after engine planning refresh."""

    workflow_id: str
    root_slug: str
    preview: Any
    graph: GraphTools
    engine: GraphEngine
    active_nodes: list[str]
    uses_micro: bool


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


def _execution_nodes(reader: StandardsReader, execution_order: tuple[str, ...] | list[str]) -> list[str]:
    executable_types = {"calculation", "lookup", "equation"}
    nodes: list[str] = []
    for node_id in execution_order:
        node_type = str(reader.load(node_id).metadata.get("type", ""))
        if node_type in executable_types:
            nodes.append(node_id)
        elif node_type not in {
            "root",
            "workflow",
            "standard_section",
            "text",
            "parameter",
            "assumption",
            "interaction",
            "table",
            "definition",
        }:
            nodes.append(node_id)
    return nodes


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


def refresh_task_planning_state(
    task: Task,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
    allow_lightweight_refresh: bool = True,
) -> PlanningRefreshFinalizeContext | None:
    """Recompute graph-derived planning state and materialize EngineeringPlan when required."""
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if not workflow_id:
        return None

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
        micro = engine._micro_engine(reader)
        graph_store = micro.store if micro is not None else None
        gate_fields: frozenset[str] = frozenset()
        if graph_store is not None:
            from engine.graph.expansion_policy import collect_workflow_expansion_fields

            resolved_root = graph_store.resolve_node_id(root_slug) or root_slug
            gate_fields = frozenset(collect_workflow_expansion_fields(graph_store, resolved_root))
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
                expansion_gate_fields=gate_fields,
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

    phase_key = phased.current_phase.value
    phase_submittable = sorted(
        {
            str(item)
            for item in (phased.phase_missing.get(phase_key) or [])
            if str(item).strip()
        }
    )
    preliminary_snapshot = build_planning_structure_snapshot(
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
        submittable_parameters=phase_submittable or None,
    )
    if (
        defaults_added
        and signature_before_propose is not None
        and preliminary_snapshot is not None
        and structure_unchanged_for_skip(signature_before_propose, preliminary_snapshot)
    ):
        defaults_added = False
    stored_signature = task.outputs.get("planning_structure_signature")
    skip_goal_tree = (
        allow_lightweight_refresh
        and not defaults_added
        and preliminary_snapshot is not None
        and isinstance(stored_signature, dict)
        and structure_unchanged_for_skip(stored_signature, preliminary_snapshot)
    )

    if skip_goal_tree:
        with perf_span("planning_refresh_skipped", "planner", notes="structure_unchanged"):
            from engine.planner.plan_phases import refresh_stored_plan_input_strategy
            from engine.planning.plan_projection_sync import sync_plan_projections

            refresh_stored_plan_input_strategy(task, dict(active_facts(task)))
            sync_plan_projections(task)
    else:
        refresh_goal_tree(
            task,
            reader,
            preview=preview,
            question_map=question_map,
            phased=phased,
            root_slug=root_slug,
        )

    from engine.planner.plan_selection import planner_submittable_fields_from_task

    submittable = planner_submittable_fields_from_task(task)
    if submittable is None:
        submittable = phase_submittable
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

    if snapshot is not None:
        task.outputs["planning_structure_signature"] = snapshot

    return PlanningRefreshFinalizeContext(
        workflow_id=workflow_id,
        root_slug=root_slug,
        preview=preview,
        graph=graph,
        engine=engine,
        active_nodes=active_nodes,
        uses_micro=uses_micro,
    )
