"""Canonical task-state projection with separated execution, progress, graph, and values layers."""

from __future__ import annotations

from typing import Any

from api.equation_inputs_display import format_value_with_unit_for_display
from engine.navigation import collect_all_missing, submittable_parameter_ids, timeline_step_id_for_parameter
from engine.inspection.value_classification import is_inspection_excluded_output_key
from engine.planner.goal_navigation import build_current_ask, next_actionable_goal
from engine.planner.workflow_goal_metadata import workflow_display_title_from_node
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.reference.parameter_keys import param_node_id_for_input
from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import (
    current_phase,
    missing_assumption_keys,
    missing_input_keys,
    planning_projection,
)
from engine.state.state_manager import TaskStateManager
from engine.state.workflow_parameters import build_workflow_parameters
from models.fact import (
    Fact,
    SourceType,
    ValidationStatus,
    fact_scalar_value,
    fact_unit,
)
from models.goal import GoalClass, SatisfactionStatus, goal_parameter_key
from models.task import Task, TaskStatus

_GRAPH_METADATA_KEYS = frozenset(
    {
        "selected_nodes",
        "graph_input_order",
        "graph_step_titles",
        "collection_field_order",
        "phase_allowed_fields",
        "path_decision",
        "timeline_input_order",
        "selected_root",
        "graph_root",
        "graph_version",
        "workflow",
        "active_definition_node",
        "alternative_paths",
        "edit_session",
        "display_name",
    }
)

_CONTROL_OUTPUT_KEYS = frozenset(
    {
        "workflow",
        "selected_root",
        "graph_root",
        "graph_version",
        "_execution_trace",
        "_validation_trace",
        "_lifecycle_events",
        "_execution_events",
        "_replay_snapshot",
        "_inspection_breakpoint",
        "_provenance_warnings",
        "task_state_errors",
    }
)

_EQUATION_SYMBOL_ALIASES = frozenset({"S", "P", "D", "E_j", "W", "Y", "c", "t", "t_m", "MAWP"})

_DERIVED_OUTPUT_KEYS = frozenset(
    {
        "required_thickness",
        "minimum_required_thickness",
        "mawp",
        "allowable_stress",
    }
)

_INPUT_STEP_IDS = frozenset(
    {
        "report",
        "thickness",
        "mawp",
        "required_wall_thickness",
        "minimum_required_thickness",
    }
)

_CATALOG_DISPLAY_TITLES = {
    PIPE_WALL_THICKNESS_DESIGN: "Pipe Wall Thickness Design",
    MAWP_DESIGN: "Maximum Allowable Working Pressure (MAWP)",
}


def build_canonical_task_state(
    task: Task,
    manager: TaskStateManager,
    *,
    planning: dict[str, Any] | None = None,
    progress_steps: list[dict[str, Any]] | None = None,
    reader: StandardsReader | None = None,
) -> dict[str, Any]:
    """Build the layered canonical task state from runtime task data."""
    resolved_planning = planning if planning is not None else planning_projection(task)
    steps = progress_steps or []
    submittable = submittable_parameter_ids(task, resolved_planning)
    blocker = _build_current_blocker(task, resolved_planning, submittable, reader=reader)
    missing_inputs = _resolve_missing_inputs(task, resolved_planning, blocker, submittable)
    values = _build_engineering_values(task, reader=reader)
    graph = _build_graph_state(task, resolved_planning, blocker)
    execution = _build_execution(task, resolved_planning, blocker, graph)
    progress = _build_progress(
        task,
        resolved_planning,
        steps,
        missing_inputs=missing_inputs,
        submittable=submittable,
        blocker=blocker,
    )

    status = _canonical_status(task)
    payload: dict[str, Any] = {
        "task": {
            "id": task.task_id,
            "workflow_id": _task_workflow_id(task),
            "name": _task_display_name(task, reader=reader),
            "status": status,
        },
        "execution": execution,
        "values": values,
        "progress": progress,
        "graph": graph,
        "lookup_results": _lookup_results(task),
        "debug": {
            "warnings": list(task.warnings),
        },
    }
    return payload


def build_task_inspector_summary(task_state: dict[str, Any]) -> dict[str, Any]:
    """Compact inspector view derived from canonical task state."""
    task = task_state.get("task") or {}
    execution = task_state.get("execution") or {}
    progress = task_state.get("progress") or {}
    graph = task_state.get("graph") or {}
    values = task_state.get("values") or {}
    debug = task_state.get("debug") or {}

    resolved_inputs: list[dict[str, Any]] = []
    for field, entry in sorted(values.items()):
        if not isinstance(entry, dict):
            continue
        if entry.get("status") not in {"confirmed", "validated"}:
            continue
        display = entry.get("display_value")
        if display is None:
            display = _format_display(entry.get("value"), entry.get("unit"))
        if display is None:
            continue
        resolved_inputs.append(
            {
                "field": field,
                "symbol": entry.get("symbol"),
                "display_value": str(display),
                "source": entry.get("source") or "unknown",
            }
        )

    branch_decisions = []
    for decision in (graph.get("selected_branch_decisions") or {}).values():
        if isinstance(decision, dict):
            branch_decisions.append(decision)

    pending_calculations = [
        step["id"]
        for step in (progress.get("steps") or [])
        if isinstance(step, dict)
        and step.get("status") in {"pending", "blocked", "active"}
        and step.get("id") not in _INPUT_STEP_IDS
        and step.get("id") not in (progress.get("missing_inputs") or [])
    ]
    # Include calculation milestones explicitly when still pending
    for calc_id in ("required_wall_thickness", "minimum_required_thickness", "report", "thickness", "mawp"):
        step = next(
            (item for item in (progress.get("steps") or []) if isinstance(item, dict) and item.get("id") == calc_id),
            None,
        )
        if step and step.get("status") in {"pending", "blocked"} and calc_id not in pending_calculations:
            pending_calculations.append(calc_id)

    expanded = graph.get("expanded_node_ids") or graph.get("selected_subgraph_node_ids") or []
    active = graph.get("active_node_ids") or []
    resolved_nodes = graph.get("resolved_node_ids") or []
    pending_nodes = graph.get("pending_node_ids") or []

    return {
        "status": task.get("status"),
        "phase": execution.get("phase"),
        "current_blocker": execution.get("current_blocker"),
        "resolved_inputs": resolved_inputs,
        "missing_inputs": list(progress.get("missing_inputs") or []),
        "selected_branch_decisions": branch_decisions,
        "pending_calculations": pending_calculations,
        "execution_graph_summary": {
            "expanded_count": len(expanded),
            "active_count": len(active),
            "resolved_count": len(resolved_nodes),
            "pending_count": len(pending_nodes),
        },
        "warnings": list(debug.get("warnings") or []),
    }


def validate_task_state_invariants(task_state: dict[str, Any]) -> list[str]:
    """Return human-readable invariant violations for canonical task state."""
    violations: list[str] = []
    task = task_state.get("task") or {}
    execution = task_state.get("execution") or {}
    progress = task_state.get("progress") or {}
    values = task_state.get("values") or {}
    graph = task_state.get("graph") or {}

    status = task.get("status")
    blocker = execution.get("current_blocker") or {}
    blocker_type = blocker.get("type")

    if status == "awaiting_input" and blocker_type in {None, "none"}:
        violations.append("awaiting_input requires execution.current_blocker.type != 'none'")

    if blocker_type == "missing_input":
        field = blocker.get("field")
        missing = progress.get("missing_inputs") or []
        if field and field not in missing:
            violations.append(f"current_blocker.field {field!r} must appear in progress.missing_inputs")

    for key in _GRAPH_METADATA_KEYS:
        if key in values:
            violations.append(f"graph metadata {key!r} must not appear in values")

    expanded = set(graph.get("expanded_node_ids") or graph.get("selected_subgraph_node_ids") or [])
    active = set(graph.get("active_node_ids") or [])
    if expanded and active == expanded:
        violations.append("graph.active_node_ids must not equal the full expanded graph")

    for key, entry in values.items():
        if key in _EQUATION_SYMBOL_ALIASES and key not in _DERIVED_OUTPUT_KEYS:
            violations.append(f"equation alias {key!r} must not be persisted in values")
        if not isinstance(entry, dict):
            violations.append(f"values[{key!r}] must be a structured EngineeringValue object")

    if "timeline" in progress:
        violations.append("progress.timeline is deprecated; use progress.steps only")

    return violations


def build_legacy_task_state_view(
    canonical: dict[str, Any],
    *,
    legacy_extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Flatten canonical state into legacy API fields for backward compatibility."""
    task = canonical.get("task") or {}
    execution = canonical.get("execution") or {}
    progress = canonical.get("progress") or {}
    graph = canonical.get("graph") or {}
    steps = list(progress.get("steps") or [])

    legacy: dict[str, Any] = {
        "task_id": task.get("id"),
        "name": task.get("name"),
        "workflow_id": task.get("workflow_id"),
        "status": task.get("status"),
        "active_nodes": list(graph.get("expanded_node_ids") or graph.get("selected_subgraph_node_ids") or []),
        "progress": {
            "steps": steps,
            "timeline": steps,  # deprecated alias
            "completed_count": progress.get("completed_count", 0),
            "total_count": progress.get("total_count", len(steps)),
            "current_step_id": progress.get("current_step_id"),
            "missing_inputs": list(progress.get("missing_inputs") or []),
            "missing_assumptions": list(progress.get("missing_assumptions") or []),
            "submittable_parameters": list(progress.get("submittable_parameters") or []),
        },
        "execution_context": {
            "state": {
                "current_phase": execution.get("phase"),
            },
        },
        "current_node": execution.get("current_execution_node_id"),
        "values": canonical.get("values"),
        "graph": graph,
        "lookup_results": canonical.get("lookup_results"),
    }
    if legacy_extras:
        legacy.update(legacy_extras)
    return legacy


def _canonical_status(task: Task) -> str:
    raw = task.status.value
    if raw == TaskStatus.AWAITING_INPUT.value:
        return "awaiting_input"
    if raw == TaskStatus.COMPLETED.value:
        return "completed"
    if raw == TaskStatus.INVALIDATED.value:
        return "failed"
    if raw in {TaskStatus.ACTIVE.value, TaskStatus.IN_PROGRESS.value}:
        return "running"
    if raw == TaskStatus.PAUSED.value:
        return "idle"
    return raw


def _task_workflow_id(task: Task) -> str:
    workflow = task.outputs.get("workflow")
    if isinstance(workflow, str) and workflow:
        return workflow
    return ""


def _task_display_name(task: Task, *, reader: StandardsReader | None = None) -> str:
    custom = task.outputs.get("display_name")
    if isinstance(custom, str) and custom.strip():
        return custom.strip()
    workflow_id = _task_workflow_id(task)
    if not workflow_id:
        return task.task_id
    if reader is not None:
        node_title = workflow_display_title_from_node(reader, workflow_id)
        if node_title:
            return node_title
    catalog_title = _CATALOG_DISPLAY_TITLES.get(workflow_id)
    if catalog_title:
        return catalog_title
    return workflow_id.replace("_", " ").title()


def _build_current_blocker(
    task: Task,
    planning: dict[str, Any],
    submittable: list[str],
    *,
    reader: StandardsReader | None,
) -> dict[str, Any]:
    if task.status != TaskStatus.AWAITING_INPUT:
        return {"type": "none"}

    ask = build_current_ask(task, planning, reader=reader)
    if isinstance(ask, dict) and ask.get("kind") == "input":
        param = ask.get("parameter_id")
        if isinstance(param, str) and param.strip():
            field = timeline_step_id_for_parameter(task, param)
            return {
                "type": "missing_input",
                "field": field,
                "parameter_node_id": param_node_id_for_input(field),
            }

    from engine.planner.plan_selection import task_has_stored_engineering_plan

    if task_has_stored_engineering_plan(task):
        return {"type": "none"}

    goal = next_actionable_goal(task)
    if goal is not None:
        field = goal_parameter_key(goal)
        return {
            "type": "missing_input",
            "field": field,
            "parameter_node_id": param_node_id_for_input(field),
        }

    if submittable:
        field = submittable[0]
        return {
            "type": "missing_input",
            "field": field,
            "parameter_node_id": param_node_id_for_input(field),
        }

    missing_assumptions = missing_assumption_keys(task)
    if missing_assumptions:
        field = missing_assumptions[0]
        return {
            "type": "missing_assumption",
            "field": field,
            "parameter_node_id": param_node_id_for_input(field),
        }

    phase = str(planning.get("current_phase") or current_phase(task))
    phase_missing = planning.get("phase_missing") or {}
    if isinstance(phase_missing, dict) and phase:
        fields = phase_missing.get(phase) or []
        if fields:
            field = str(fields[0])
            return {
                "type": "missing_input",
                "field": field,
                "parameter_node_id": param_node_id_for_input(field),
            }

    if task.status == TaskStatus.INVALIDATED:
        message = task.warnings[0] if task.warnings else "Validation failed"
        return {"type": "validation_error", "message": message}

    return {"type": "none"}


def _resolve_missing_inputs(
    task: Task,
    planning: dict[str, Any],
    blocker: dict[str, Any],
    submittable: list[str],
) -> list[str]:
    missing: set[str] = set(missing_input_keys(task))
    all_missing = collect_all_missing(planning)
    missing.update(all_missing)

    phase = str(planning.get("current_phase") or current_phase(task))
    phase_missing = planning.get("phase_missing") or {}
    if isinstance(phase_missing, dict) and phase:
        missing.update(str(item) for item in (phase_missing.get(phase) or []))

    if blocker.get("type") == "missing_input" and blocker.get("field"):
        missing.add(str(blocker["field"]))

    for param in submittable:
        fact = task.fact_store.active_fact(param)
        if fact is None or fact.validation.status not in {
            ValidationStatus.CONFIRMED,
            ValidationStatus.VALIDATED,
        }:
            missing.add(param)

    return sorted(missing)


def _build_execution(
    task: Task,
    planning: dict[str, Any],
    blocker: dict[str, Any],
    graph: dict[str, Any],
) -> dict[str, Any]:
    phase = str(planning.get("current_phase") or current_phase(task))
    active_ids = graph.get("active_node_ids") or []
    current_node = active_ids[0] if active_ids else None
    if blocker.get("parameter_node_id"):
        current_node = blocker["parameter_node_id"]

    return {
        "phase": phase,
        "active_definition_node_id": task.outputs.get("active_definition_node"),
        "current_execution_node_id": current_node,
        "current_blocker": blocker,
    }


def _build_graph_state(
    task: Task,
    planning: dict[str, Any],
    blocker: dict[str, Any],
) -> dict[str, Any]:
    expanded = list(
        planning.get("selected_nodes")
        or task.outputs.get("selected_nodes")
        or task.active_nodes
        or []
    )
    active: list[str] = []
    if blocker.get("parameter_node_id"):
        active.append(str(blocker["parameter_node_id"]))
    elif blocker.get("field"):
        active.append(param_node_id_for_input(str(blocker["field"])))

    if not active and blocker.get("type") == "none":
        definition_node = task.outputs.get("active_definition_node")
        if isinstance(definition_node, str) and definition_node.strip():
            active.append(definition_node.strip())

    resolved: list[str] = []
    trace = task.outputs.get("_execution_trace")
    if isinstance(trace, list):
        for item in trace:
            if isinstance(item, dict) and item.get("node_id"):
                node_id = str(item["node_id"])
                if node_id not in resolved:
                    resolved.append(node_id)

    pending: list[str] = []
    for goal in task.goal_store.goals.values():
        if goal.goal_class == GoalClass.CALCULATION and goal.satisfaction.status not in {
            SatisfactionStatus.SATISFIED,
            SatisfactionStatus.SUPERSEDED,
        }:
            target = str(goal.metadata.get("target_node") or goal.key)
            if target and target not in pending:
                pending.append(target)

    branch_decisions: dict[str, Any] = {}
    path_decision = planning.get("path_decision") or task.outputs.get("path_decision")
    if isinstance(path_decision, dict):
        field = str(path_decision.get("field") or path_decision.get("parameter") or "pressure_loading")
        branch_decisions[field] = {
            "field": field,
            "value": str(path_decision.get("value") or path_decision.get("choice") or ""),
            "selected_node": str(path_decision.get("selected_node") or ""),
        }

    return {
        "selected_branch_decisions": branch_decisions,
        "expanded_node_ids": expanded,
        "active_node_ids": active,
        "resolved_node_ids": resolved,
        "pending_node_ids": pending,
        "selected_subgraph_node_ids": expanded,
    }


def _build_progress(
    task: Task,
    planning: dict[str, Any],
    steps: list[dict[str, Any]],
    *,
    missing_inputs: list[str],
    submittable: list[str],
    blocker: dict[str, Any],
) -> dict[str, Any]:
    canonical_steps = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        canonical_steps.append(
            {
                "id": step.get("id"),
                "title": step.get("title"),
                "status": step.get("status"),
                "display_value": step.get("display_value"),
                "editable": bool(step.get("editable")),
                "hint": step.get("hint"),
                "parameter_node_id": (
                    param_node_id_for_input(str(step["id"]))
                    if step.get("id") and step.get("id") not in _INPUT_STEP_IDS
                    else None
                ),
                "provenance_id": step.get("provenance", {}).get("id") if isinstance(step.get("provenance"), dict) else None,
            }
        )

    completed = sum(1 for step in canonical_steps if step.get("status") == "done")
    current_step_id = None
    if blocker.get("field"):
        current_step_id = str(blocker["field"])
    else:
        active = next((s for s in canonical_steps if s.get("status") == "active"), None)
        if active:
            current_step_id = active.get("id")

    if task.status == TaskStatus.AWAITING_INPUT and not submittable and missing_inputs:
        submittable = [missing_inputs[0]]

    return {
        "current_step_id": current_step_id,
        "completed_count": completed,
        "total_count": len(canonical_steps),
        "steps": canonical_steps,
        "missing_inputs": missing_inputs,
        "missing_assumptions": list(missing_assumption_keys(task)),
        "submittable_parameters": submittable,
    }


def _build_engineering_values(
    task: Task,
    *,
    reader: StandardsReader | None,
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    fact_keys = set(task.fact_store.active_facts().keys())

    if reader is not None:
        parameters = build_workflow_parameters(task, reader=reader, active_nodes=set(task.active_nodes))
        for name, param in parameters.items():
            if name in _GRAPH_METADATA_KEYS or is_inspection_excluded_output_key(name):
                continue
            if name in _EQUATION_SYMBOL_ALIASES and name not in fact_keys:
                continue
            if name.endswith("_unit") or name.endswith("_lookup"):
                continue
            values[name] = {
                "name": name,
                "value": param.value,
                "unit": param.unit or None,
                "canonical_value": param.value,
                "canonical_unit": param.canonical_unit,
                "dimension": param.dimension,
                "symbol": param.symbol,
                "source": _normalize_source(param.source),
                "status": _normalize_status(param.status),
                "display_value": _format_display(param.value, param.unit),
                "parameter_node_id": param.param_node_id,
            }
        return values

    for name, fact in task.fact_store.active_facts().items():
        values[name] = _engineering_value_from_fact(name, fact)

    for key, value in task.outputs.items():
        if is_inspection_excluded_output_key(key) or key in _GRAPH_METADATA_KEYS:
            continue
        if key.endswith("_lookup") or key.endswith("_unit"):
            continue
        if key in _EQUATION_SYMBOL_ALIASES and key not in fact_keys:
            continue
        if key in values:
            continue
        if isinstance(value, (dict, list)):
            continue
        values[key] = {
            "name": key,
            "value": value,
            "unit": _output_unit(task, key),
            "source": "derived",
            "status": "confirmed",
            "display_value": _format_display(value, _output_unit(task, key)),
            "parameter_node_id": param_node_id_for_input(key),
        }
    return values


def _engineering_value_from_fact(name: str, fact: Fact) -> dict[str, Any]:
    unit = fact_unit(fact)
    value = fact_scalar_value(fact)
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "symbol": fact.symbol,
        "source": _normalize_source(fact.source.source_type.value),
        "status": _normalize_status(fact.validation.status.value),
        "display_value": _format_display(value, unit),
        "parameter_node_id": fact.parameter or param_node_id_for_input(name),
    }


def _lookup_results(task: Task) -> dict[str, Any]:
    return {
        key: value
        for key, value in task.outputs.items()
        if key.endswith("_lookup") or key.endswith("_lookup_result")
    }


def _normalize_source(source: str) -> str:
    mapping = {
        "user_input": "user_input",
        "table_lookup": "lookup",
        "lookup": "lookup",
        "equation": "derived",
        "derived": "derived",
        "default_confirmed": "user_input",
        "system": "system",
        "import": "user_input",
    }
    return mapping.get(source, source)


def _normalize_status(status: str) -> str:
    if status in {"confirmed", "validated"}:
        return "confirmed"
    if status in {"pending", "proposed"}:
        return "pending"
    if status in {"rejected", "conflicting", "invalid"}:
        return "invalid"
    if status == "superseded":
        return "missing"
    return status


def _format_display(value: Any, unit: str | None) -> str | None:
    if value is None:
        return None
    return format_value_with_unit_for_display(value, unit)


def _output_unit(task: Task, key: str) -> str | None:
    unit_key = f"{key}_unit"
    unit = task.outputs.get(unit_key)
    return str(unit) if unit is not None else None
