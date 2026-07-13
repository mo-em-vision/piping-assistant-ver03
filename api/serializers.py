"""Serialize backend models for the desktop REST API."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

ProjectionMode = Literal["interactive", "full"]

from api.error_catalog import enrich_api_error_payload
from api.flow_guidance import build_flow_guidance_payload
from api.flow_guidance_transcript import load_flow_guidance_transcript_blocks
from api.completion_next_workflows_transcript import flatten_transcript_blocks_for_api
from api.equation_inputs_display import (
    _input_display_value,
    format_thickness_result_display,
    format_value_with_unit_for_display,
)
from api.json_encoding import dumps as json_dumps, json_safe
from api.node_calculation_summaries import build_node_calculation_summaries
from api.node_context import active_node_context_for_task
from api.node_provenance import step_provenance
from api.output_blocks import build_display_outputs
from api.parameter_definitions import build_parameter_definitions
from api.reference_links import enrich_display_output_dict, enrich_flow_guidance_payload
from api.workflow_timeline import (
    collect_all_missing,
    is_mawp_task,
    is_pipe_wall_thickness_task,
    mawp_input_step_done,
    mawp_step_title,
    pipe_wall_input_step_done,
    pipe_wall_step_title,
    revealed_input_ids,
    revealed_pipe_wall_input_ids,
    submittable_parameter_ids,
    timeline_step_id_for_parameter,
    workflow_input_step_done,
    workflow_step_title,
)
from api.workflow_bootstrap import task_ready_for_execution
from api.parameter_edit import active_edit_parameter, is_timeline_parameter_editable
from engine.graph.definition_equations import (
    has_execution_trace,
    pending_definition_equation_inputs,
)
from engine.reference.parameter_keys import MATERIAL_GRADE_KEY
from engine.reference.standards_reader import StandardsReader
from engine.graph.graph_engine import GraphEngine
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.state.authority_context_projection import authority_context_summary
from engine.state.execution_context_projection import execution_context_summary
from engine.planner.goal_navigation import build_current_ask
from engine.state.goal_projection import (
    legacy_goal_map_for_task,
    planning_projection,
)
from api.workflow_display import workflow_display_meta
from engine.state.task_state_canonical import (
    build_canonical_task_state,
    build_legacy_task_state_view,
    build_task_inspector_summary,
    validate_task_state_invariants,
)
from engine.inspection.performance_trace import perf_span
from engine.state.state_manager import TaskStateManager
from models.fact import Fact, ValidationStatus, fact_scalar_value, fact_to_dict, fact_unit
from models.task import Task, TaskStatus

WORKFLOW_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": PIPE_WALL_THICKNESS_DESIGN,
        "name": "Pipe Thickness Calculation",
        "display_title": "Pipe Wall Thickness Design",
        "subtitle": "ASME B31.3 §304.1 — Pressure design thickness for straight pipe",
        "standard_ref": "ASME B31.3 §304.1",
        "description": "ASME B31.3 wall thickness design workflow",
        "discipline": "Piping",
        "available": True,
    },
    {
        "id": MAWP_DESIGN,
        "name": "Maximum Allowable Working Pressure (MAWP)",
        "description": "Calculate MAWP of piping components per ASME B31.3",
        "discipline": "Piping",
        "available": True,
    },
    {
        "id": "flange_selection",
        "name": "Flange Selection",
        "description": "Select flanges for piping systems",
        "discipline": "Piping",
        "available": False,
    },
    {
        "id": "material_selection",
        "name": "Material Selection",
        "description": "Choose materials from standards databases",
        "discipline": "Materials",
        "available": False,
    },
    {
        "id": "tank_design",
        "name": "Tank Design",
        "description": "API 650 storage tank design workflow",
        "discipline": "Mechanical",
        "available": False,
    },
    {
        "id": "standards_lookup",
        "name": "Standards Lookup",
        "description": "Search and navigate engineering standards",
        "discipline": "Reference",
        "available": False,
    },
)

_WORKFLOW_BY_ID = {item["id"]: item for item in WORKFLOW_CATALOG}

_HIDDEN_UNITS = frozenset({"dimensionless", ""})


def workflow_catalog(reader: StandardsReader | None = None) -> list[dict[str, Any]]:
    if reader is not None:
        dynamic = GraphEngine().list_workflows(reader)
        if dynamic:
            catalog = [dict(item) for item in dynamic]
            catalog.extend(
                item
                for item in WORKFLOW_CATALOG
                if item["id"] not in {w["id"] for w in catalog}
            )
            return catalog
    return [dict(item) for item in WORKFLOW_CATALOG]


def workflow_catalog_legacy() -> list[dict[str, Any]]:
    return [dict(item) for item in WORKFLOW_CATALOG]


def _workflow_meta(workflow_id: str, reader: StandardsReader | None = None) -> dict[str, Any]:
    if reader is not None:
        for item in workflow_catalog(reader):
            if item["id"] == workflow_id or item.get("node_id") == workflow_id:
                return item
    return _WORKFLOW_BY_ID.get(
        workflow_id,
        {
            "id": workflow_id,
            "name": workflow_id.replace("_", " ").title(),
            "description": "",
            "discipline": "Engineering",
            "available": False,
        },
    )


def _task_workflow_id(task: Task) -> str:
    workflow = task.outputs.get("workflow")
    if isinstance(workflow, str) and workflow:
        return workflow
    if task.task_id.startswith("pipe-wall-thickness"):
        return PIPE_WALL_THICKNESS_DESIGN
    return ""


_OUTPUT_DEBUG_KEYS = frozenset(
    {
        "engineering_plan",
        "planner_inspector_summary",
        "planner_debug_projection",
        "engineering_plan_view",
        "_execution_trace",
        "_expansion_traversal_trace",
        "_skipped_trace",
        "_validation_trace",
    }
)


def _public_task_outputs(task: Task) -> dict[str, Any]:
    """Task outputs for API consumers — omits verbose internal planner blobs."""
    outputs = dict(task.outputs)
    for key in _OUTPUT_DEBUG_KEYS:
        outputs.pop(key, None)
    return json_safe(outputs)


def _engineering_plan_view_for_task(task: Task) -> dict[str, Any] | None:
    from engine.planner.plan_inspector import engineering_plan_view_for_task

    view = engineering_plan_view_for_task(task)
    return json_safe(view) if view else None


def _canonical_engineering_plan_for_task(task: Task) -> dict[str, Any] | None:
    from engine.planner.plan_inspector import canonical_engineering_plan_for_task

    plan = canonical_engineering_plan_for_task(task)
    return json_safe(plan) if plan else None


def _task_display_name(task: Task) -> str:
    custom = task.outputs.get("display_name")
    if isinstance(custom, str) and custom.strip():
        return custom.strip()
    workflow_id = _task_workflow_id(task)
    if not workflow_id:
        return task.task_id
    meta = _workflow_meta(workflow_id)
    return workflow_display_meta(workflow_id, meta)["display_title"]


def _fact_to_dict(fact: Fact) -> dict[str, Any]:
    payload = fact_to_dict(fact)
    value = fact_scalar_value(fact)
    unit = fact_unit(fact)
    payload["display_value"] = _format_display_value(value, unit)
    return json_safe(payload)


def _input_to_dict(value: Fact) -> dict[str, Any]:
    """Legacy alias for fact serialization."""
    return _fact_to_dict(value)


def _format_display_value(value: Any, unit: str | None) -> str | None:
    return format_value_with_unit_for_display(value, unit)


def _thickness_step_display_value(task: Task, thickness: float) -> str:
    unit = str(
        task.outputs.get("thickness_unit")
        or task.outputs.get("required_thickness_unit")
        or task.outputs.get("t_unit")
        or "mm"
    )
    return format_thickness_result_display(float(thickness), unit)


def _input_display(
    task: Task,
    input_id: str,
    *,
    standards_root: Path | None = None,
) -> str | None:
    if input_id == "pressure_loading":
        fact = task.fact_store.active_fact(input_id)
        if fact is None:
            return None
        return _pressure_loading_report_value(fact_scalar_value(fact))
    return _input_display_value(task, input_id, standards_root=standards_root)


def _pressure_loading_report_value(value: Any) -> str:
    if value == "internal_pressure":
        return "The pipe is internally pressurized."
    if value == "external_pressure":
        return "The pipe is externally pressurized."
    return str(value).replace("_", " ").capitalize()


def _preferred_timeline_active_input_id(
    task: Task,
    *,
    editing_parameter: str | None,
    ask_parameter_id: str | None,
    submittable_ids: list[str],
    revealed_inputs: list[str],
) -> str | None:
    if editing_parameter:
        return timeline_step_id_for_parameter(
            task, editing_parameter, revealed=revealed_inputs
        )
    if ask_parameter_id:
        return timeline_step_id_for_parameter(
            task, ask_parameter_id, revealed=revealed_inputs
        )
    if submittable_ids:
        return timeline_step_id_for_parameter(
            task, submittable_ids[0], revealed=revealed_inputs
        )
    return None


def _input_timeline_status(
    *,
    step_id: str,
    input_done: bool,
    preferred_active: str | None,
    active_assigned: bool,
) -> tuple[str, bool]:
    if input_done:
        return "done", active_assigned
    if preferred_active is not None:
        if step_id == preferred_active:
            return "active", True
        return "pending", active_assigned
    if not active_assigned:
        return "active", True
    return "pending", active_assigned


def _step(
    *,
    step_id: str,
    title: str,
    status: str,
    value: Any = None,
    unit: str | None = None,
    display_value: str | None = None,
    hint: str | None = None,
    editable: bool = False,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "id": step_id,
        "title": title,
        "status": status,
        "value": value,
        "unit": unit,
        "display_value": display_value,
        "hint": hint,
        "editable": editable,
    }
    if provenance:
        payload["provenance"] = provenance
    return payload


def _mawp_step_display_value(task: Task, mawp_pa: float) -> str:
    return format_value_with_unit_for_display(float(mawp_pa) / 1_000_000, "MPa") or f"{mawp_pa} Pa"


def _build_mawp_timeline(
    task: Task,
    planning: dict[str, Any],
    *,
    standards_root: Path | None = None,
    reader: StandardsReader | None = None,
    ask_parameter_id: str | None = None,
) -> list[dict[str, Any]]:
    phase_missing = planning.get("phase_missing") or {}
    phase_questions = planning.get("phase_questions") or {}
    current_phase = str(planning.get("current_phase") or "")

    all_missing = collect_all_missing(planning)
    revealed_inputs = revealed_input_ids(task, planning, reader=reader)
    ordered_steps: list[tuple[str, str]] = [
        (step_id, workflow_step_title(task, step_id, planning, reader=reader))
        for step_id in revealed_inputs
    ]
    ordered_steps.extend(
        [
            ("mawp", mawp_step_title("mawp", planning, task=task, reader=reader)),
            ("report", mawp_step_title("report", planning, task=task, reader=reader)),
        ]
    )

    mawp_output = task.outputs.get("mawp") or task.outputs.get("MAWP")
    mawp_done = mawp_output is not None
    report_done = task.status == TaskStatus.COMPLETED

    timeline: list[dict[str, Any]] = []
    active_assigned = False
    editing_parameter = active_edit_parameter(task)
    submittable_ids = submittable_parameter_ids(task, planning)
    preferred_active = _preferred_timeline_active_input_id(
        task,
        editing_parameter=editing_parameter,
        ask_parameter_id=ask_parameter_id,
        submittable_ids=submittable_ids,
        revealed_inputs=revealed_inputs,
    )

    for step_id, title in ordered_steps:
        if step_id == "mawp":
            if mawp_done:
                status = "done"
                hint = None
                display_value = _mawp_step_display_value(task, float(mawp_output))
            elif not active_assigned and current_phase not in {
                "expansion_assumptions",
                "path_decisions",
            }:
                status = "active"
                hint = "Waiting for MAWP calculation"
                display_value = None
                active_assigned = True
            else:
                status = "pending"
                hint = None
                display_value = None
        elif step_id == "report":
            if report_done:
                status = "done"
                hint = None
            elif mawp_done:
                status = "active"
                hint = "Generate the engineering report"
            else:
                status = "pending"
                hint = "Available after MAWP calculation completes"
            display_value = None
        else:
            if editing_parameter and step_id == editing_parameter:
                status = "active"
                hint = "Update this value in the workflow composer."
                display_value = _input_display(task, step_id, standards_root=standards_root)
                active_assigned = True
            else:
                input_done = workflow_input_step_done(task, step_id, all_missing)
                status, active_assigned = _input_timeline_status(
                    step_id=step_id,
                    input_done=input_done,
                    preferred_active=preferred_active,
                    active_assigned=active_assigned,
                )
                if status == "done":
                    hint = None
                    display_value = _input_display(task, step_id, standards_root=standards_root)
                elif status == "active":
                    hint = _step_hint(step_id, phase_missing, phase_questions, current_phase)
                    display_value = None
                else:
                    hint = None
                    display_value = None

        timeline.append(
            _step(
                step_id=step_id,
                title=title,
                status=status,
                display_value=display_value,
                hint=hint,
                editable=(
                    status == "done"
                    and is_timeline_parameter_editable(task, step_id)
                    and step_id != editing_parameter
                ),
                provenance=step_provenance(reader, task, step_id, planning) if reader else None,
            )
        )

    return timeline


def _build_pipe_wall_timeline(
    task: Task,
    planning: dict[str, Any],
    *,
    standards_root: Path | None = None,
    reader: StandardsReader | None = None,
    ask_parameter_id: str | None = None,
) -> list[dict[str, Any]]:
    phase_missing = planning.get("phase_missing") or {}
    phase_questions = planning.get("phase_questions") or {}
    current_phase = str(planning.get("current_phase") or "")

    all_missing = collect_all_missing(planning)
    definition_pending = current_phase == "definition_equation_completion" or bool(
        phase_missing.get("definition_equation_completion")
    )
    if not definition_pending and reader is not None:
        graph = task.outputs.get("graph_root") or task.outputs.get("selected_root") or task.outputs.get("workflow")
        if graph and has_execution_trace(task):
            from engine.graph.graph_engine import GraphEngine, normalize_root_id

            preview = GraphEngine().build_plan(
                task_id=task.task_id,
                root_id=normalize_root_id(str(graph)),
                inputs=dict(task.fact_store.active_facts()),
                reader=reader,
            )
            definition_pending = bool(
                pending_definition_equation_inputs(task, reader, preview.execution_order)
            )

    revealed_inputs = revealed_pipe_wall_input_ids(task, planning, reader=reader)
    ordered_steps: list[tuple[str, str]] = [
        (
            step_id,
            pipe_wall_step_title(step_id, planning, task=task, reader=reader),
        )
        for step_id in revealed_inputs
    ]
    ordered_steps.extend(
        [
            ("thickness", pipe_wall_step_title("thickness", planning, task=task, reader=reader)),
            ("report", pipe_wall_step_title("report", planning, task=task, reader=reader)),
        ]
    )

    thickness_output = task.outputs.get("required_thickness") or task.outputs.get("thickness")
    thickness_done = thickness_output is not None
    report_done = task.status == TaskStatus.COMPLETED
    submittable_ids = submittable_parameter_ids(task, planning)
    pending_input_steps = [
        step_id
        for step_id, _title in ordered_steps
        if step_id not in {"thickness", "report"}
        and not pipe_wall_input_step_done(task, step_id, all_missing)
    ]
    thickness_step_ready = (
        thickness_done
        or has_execution_trace(task)
        or (
            not submittable_ids
            and not pending_input_steps
            and task_ready_for_execution(task)
        )
    )

    timeline: list[dict[str, Any]] = []
    active_assigned = False
    editing_parameter = active_edit_parameter(task)
    preferred_active = _preferred_timeline_active_input_id(
        task,
        editing_parameter=editing_parameter,
        ask_parameter_id=ask_parameter_id,
        submittable_ids=submittable_ids,
        revealed_inputs=revealed_inputs,
    )

    for step_id, title in ordered_steps:
        if step_id == "thickness":
            if thickness_done:
                status = "done"
                hint = None
                display_value = _thickness_step_display_value(task, float(thickness_output))
            elif (
                thickness_step_ready
                and not active_assigned
                and current_phase not in {
                    "expansion_assumptions",
                    "path_decisions",
                }
            ):
                status = "active"
                hint = "Waiting for thickness calculation"
                display_value = None
                active_assigned = True
            else:
                status = "pending"
                hint = None
                display_value = None
        elif step_id == "report":
            if report_done:
                status = "done"
                hint = None
            elif thickness_done and not definition_pending:
                status = "active"
                hint = "Generate the engineering report"
            else:
                status = "pending"
                hint = (
                    "Available after minimum required thickness is calculated"
                    if definition_pending
                    else "Available after calculation completes"
                )
            display_value = None
        else:
            if editing_parameter and step_id == editing_parameter:
                status = "active"
                hint = "Update this value in the workflow composer."
                display_value = _input_display(task, step_id, standards_root=standards_root)
                active_assigned = True
            else:
                input_done = pipe_wall_input_step_done(task, step_id, all_missing)
                status, active_assigned = _input_timeline_status(
                    step_id=step_id,
                    input_done=input_done,
                    preferred_active=preferred_active,
                    active_assigned=active_assigned,
                )
                if status == "done":
                    hint = None
                    display_value = _input_display(task, step_id, standards_root=standards_root)
                elif status == "active":
                    hint = _step_hint(step_id, phase_missing, phase_questions, current_phase)
                    display_value = None
                else:
                    hint = None
                    display_value = None

        timeline.append(
            _step(
                step_id=step_id,
                title=title,
                status=status,
                display_value=display_value,
                hint=hint,
                editable=(
                    status == "done"
                    and is_timeline_parameter_editable(task, step_id)
                    and step_id != editing_parameter
                ),
                provenance=step_provenance(reader, task, step_id, planning) if reader else None,
            )
        )

    return timeline


def _step_hint(
    step_id: str,
    phase_missing: dict[str, Any],
    phase_questions: dict[str, Any],
    current_phase: str,
) -> str | None:
    if isinstance(phase_missing, dict):
        for phase, fields in phase_missing.items():
            if isinstance(fields, list) and step_id in fields:
                questions = phase_questions.get(phase) if isinstance(phase_questions, dict) else None
                if isinstance(questions, list):
                    index = fields.index(step_id)
                    if index < len(questions):
                        return str(questions[index])
    if step_id == "pressure_loading":
        return "Specify whether the pipe is internally or externally pressurized."
    if step_id == MATERIAL_GRADE_KEY:
        return "Waiting for material selection"
    if step_id == "internal_design_gage_pressure":
        return "Waiting for design pressure"
    if step_id == "pipe_schedule":
        return "Waiting for pipe schedule"
    if step_id == "actual_wall_thickness":
        return "Waiting for actual wall thickness"
    return None


def _build_progress_steps(
    task: Task,
    planning: dict[str, Any],
    *,
    standards_root: Path | None = None,
    reader: StandardsReader | None = None,
    ask_parameter_id: str | None = None,
) -> list[dict[str, Any]]:
    if is_mawp_task(task):
        return _build_mawp_timeline(
            task,
            planning,
            standards_root=standards_root,
            reader=reader,
            ask_parameter_id=ask_parameter_id,
        )
    if is_pipe_wall_thickness_task(task):
        return _build_pipe_wall_timeline(
            task,
            planning,
            standards_root=standards_root,
            reader=reader,
            ask_parameter_id=ask_parameter_id,
        )

    steps: list[dict[str, Any]] = []
    missing_inputs = set(planning.get("missing_inputs") or [])

    for input_id, fact in task.fact_store.active_facts().items():
        if input_id in missing_inputs:
            status = "active"
        elif fact.validation.status in {ValidationStatus.CONFIRMED, ValidationStatus.VALIDATED, ValidationStatus.PENDING}:
            status = "done"
        else:
            status = "pending"
        value = fact_scalar_value(fact)
        unit = fact_unit(fact)
        steps.append(
            _step(
                step_id=input_id,
                title=input_id.replace("_", " ").title(),
                status=status,
                value=value,
                unit=unit,
                display_value=_format_display_value(value, unit),
                provenance=step_provenance(reader, task, input_id, planning) if reader else None,
            )
        )

    report_status = "pending"
    if task.status == TaskStatus.COMPLETED:
        report_status = "done"
    elif steps and all(step["status"] == "done" for step in steps):
        report_status = "active"
    steps.append(
        _step(
            step_id="report",
            title="Report",
            status=report_status,
            hint=None if report_status != "pending" else "Available after calculation completes",
        )
    )
    return steps


def task_summary(task: Task) -> dict[str, Any]:
    workflow_id = _task_workflow_id(task)
    meta = _workflow_meta(workflow_id)
    planning = planning_projection(task)
    if not planning:
        planning = {}

    return {
        "id": task.task_id,
        "name": _task_display_name(task),
        "description": str(planning.get("goal") or meta["description"]),
        "discipline": meta["discipline"],
        "workflow_id": workflow_id,
        "status": task.status.value,
    }


def task_state(
    task: Task,
    manager: TaskStateManager,
    *,
    standards_root: Path | None = None,
    reader: StandardsReader | None = None,
    projection_mode: ProjectionMode = "interactive",
) -> dict[str, Any]:
    with perf_span("task_state", "serializer", notes=f"mode={projection_mode}"):
        return _task_state_impl(
            task,
            manager,
            standards_root=standards_root,
            reader=reader,
            projection_mode=projection_mode,
        )


def _task_state_impl(
    task: Task,
    manager: TaskStateManager,
    *,
    standards_root: Path | None = None,
    reader: StandardsReader | None = None,
    projection_mode: ProjectionMode = "interactive",
) -> dict[str, Any]:
    workflow_id = _task_workflow_id(task)
    meta = _workflow_meta(workflow_id)
    planning = planning_projection(task)
    if not planning:
        planning = {}

    resolved_standards_root = standards_root or (Path(__file__).resolve().parent.parent / "knowledge" / "standards")
    resolved_reader = reader or StandardsReader(resolved_standards_root, standard="asme_b31.3")

    current_ask = build_current_ask(task, planning, reader=resolved_reader)
    ask_parameter_id = None
    if isinstance(current_ask, dict) and current_ask.get("kind") == "input":
        raw_id = current_ask.get("parameter_id")
        if isinstance(raw_id, str) and raw_id.strip():
            ask_parameter_id = raw_id.strip()

    timeline = _build_progress_steps(
        task,
        planning,
        standards_root=resolved_standards_root,
        reader=resolved_reader,
        ask_parameter_id=ask_parameter_id,
    )
    step_progress = [
        {
            "step_id": step.step_id,
            "status": step.status,
            "result": json_safe(step.result),
        }
        for step in manager.list_step_progress(task.task_id)
    ]

    completed = sum(1 for step in timeline if step["status"] == "done")
    active = next(
        (step for step in timeline if step["status"] == "active" and step["id"] not in {"report", "thickness"}),
        None,
    )
    if active is None:
        active = next((step for step in timeline if step["status"] == "active"), None)

    active_node_context = active_node_context_for_task(task, resolved_reader)

    timeline_active_id = None
    if ask_parameter_id:
        revealed = revealed_input_ids(task, planning, reader=resolved_reader)
        timeline_active_id = timeline_step_id_for_parameter(
            task, ask_parameter_id, revealed=revealed
        )

    with perf_span("canonical_task_state", "serializer"):
        canonical = build_canonical_task_state(
            task,
            manager,
            planning=planning,
            progress_steps=timeline,
            reader=resolved_reader,
        )
    invariant_violations = validate_task_state_invariants(canonical)
    if invariant_violations:
        canonical.setdefault("debug", {})["invariant_violations"] = invariant_violations

    canonical_progress = canonical.get("progress") or {}
    canonical_graph = canonical.get("graph") or {}
    canonical_execution = canonical.get("execution") or {}
    current_step_id = (
        timeline_active_id
        or canonical_progress.get("current_step_id")
        or (active["id"] if active else None)
    )
    if current_step_id:
        canonical_progress = {**canonical_progress, "current_step_id": current_step_id}

    include_debug_projections = projection_mode == "full"
    inspector_summary = None
    if include_debug_projections:
        inspector_summary = build_task_inspector_summary({**canonical, "progress": canonical_progress})

    with perf_span("engineering_plan_projection", "serializer", notes=f"mode={projection_mode}"):
        legacy_extras: dict[str, Any] = {
            "discipline": meta["discipline"],
            "description": str(planning.get("goal") or meta["description"]),
            "workflow_display": workflow_display_meta(workflow_id, meta, reader=resolved_reader),
            "facts": {key: _fact_to_dict(value) for key, value in task.fact_store.active_facts().items()},
            "execution_context": execution_context_summary(task),
            "authority_context": authority_context_summary(task),
            "outputs": _public_task_outputs(task),
            "warnings": list(task.warnings),
            "parameters": build_parameter_definitions(task, reader=resolved_reader),
            "node_calculations": build_node_calculation_summaries(task, resolved_reader),
            "active_node_context": active_node_context,
            "current_ask": current_ask,
            "options": {
                "available_workflows": [item for item in WORKFLOW_CATALOG if item["available"]],
            },
            "errors": _build_task_errors(task),
            "workflow_state": workflow_state_payload(
                manager,
                task.task_id,
                reader=resolved_reader,
            ),
        }
        if include_debug_projections:
            legacy_extras["inspector_summary"] = inspector_summary
            with perf_span("legacy_goal_map_projection", "serializer"):
                legacy_extras["legacy_goal_map"] = legacy_goal_map_for_task(task)
            with perf_span("engineering_plan_to_dict", "serializer"):
                legacy_extras["engineering_plan"] = _canonical_engineering_plan_for_task(task)
            with perf_span("engineering_plan_view", "serializer"):
                legacy_extras["engineering_plan_view"] = _engineering_plan_view_for_task(task)
        with perf_span("display_output_projection", "serializer"):
            from api.center_panel_block_registry import filter_center_panel_blocks
            from models.display_role import resolve_display_block

            legacy_extras["display_outputs"] = filter_center_panel_blocks(
                [
                    resolve_display_block(
                        enrich_display_output_dict(item, resolved_reader, task=task)
                    )
                    for item in build_display_outputs(
                        task,
                        standards_root=resolved_standards_root,
                        reader=resolved_reader,
                    )
                ]
            )
        with perf_span("flow_guidance", "serializer"):
            transcript_blocks = load_flow_guidance_transcript_blocks(task)
            flow_guidance_payload = build_flow_guidance_payload(
                task,
                resolved_reader,
                transcript_blocks=transcript_blocks,
            )
            flow_guidance_payload["transcript_blocks"] = flatten_transcript_blocks_for_api(
                transcript_blocks,
            )
            legacy_extras["flow_guidance"] = enrich_flow_guidance_payload(
                flow_guidance_payload,
                resolved_reader,
            )
    legacy_extras["progress"] = {
        **canonical_progress,
        "steps": timeline,
        "timeline": timeline,  # deprecated alias for UI backward compatibility
        "step_progress": step_progress,
    }

    payload = build_legacy_task_state_view(canonical, legacy_extras=legacy_extras)
    payload["status"] = task.status.value
    if include_debug_projections:
        payload["canonical"] = json_safe(canonical)
        payload["inspector_summary"] = json_safe(inspector_summary)
    with perf_span("response_serialization", "serializer"):
        return json_safe(payload)


def workflow_state_payload(
    manager: TaskStateManager,
    task_id: str,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any]:
    return json_safe(manager.get_workflow_state(task_id, reader=reader))


def _build_task_errors(task: Task) -> list[dict[str, Any]]:
    if task.status != TaskStatus.INVALIDATED:
        return []

    message = "The engineering calculation could not complete with the current task state."
    if task.warnings:
        message = str(task.warnings[0])

    details: dict[str, Any] = {"task_id": task.task_id}
    if len(task.warnings) > 1:
        details["warnings"] = list(task.warnings)

    return [enrich_api_error_payload("calculation_failed", message, details=details)]
