"""Build ReportData from task state and standards knowledge."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from api.output_blocks import build_display_outputs
from engine.graph.graph_engine import GraphEngine, normalize_root_id
from engine.navigation.task_missing_inputs import missing_inputs_for_task, resolve_task_workflow_id
from engine.navigation.timeline_completion import _GOAL_OUTPUT_KEYS
from engine.planner.workflow_goal_metadata import (
    resolve_root_goal_spec,
    workflow_display_title_from_node,
    workflow_report_documentation,
    workflow_title_for_goal,
)
from engine.reports.number_format import format_report_number
from engine.reference.standards_reader import StandardsReader
from engine.reports.block_renderer import blocks_to_display_sections, human_input_label
from engine.reports.template_registry import resolve_template_name
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import active_facts
from models.fact import Fact, fact_scalar_value, fact_unit
from models.report import (
    ReportData,
    ReportDecision,
    ReportInputEntry,
    ReportOverride,
    ReportSection,
    ReportTraversalStep,
    ReportVersionInfo,
    ReportWarning,
    TraceabilityEntry,
)
from models.task import Task, TaskStatus

_GOAL_CONCLUSION_FIELDS = {
    "minimum_required_thickness": (
        ("t_m", "minimum_required_thickness"),
        ("required_thickness", "t"),
    ),
    "maximum_allowable_working_pressure": (
        ("mawp", "MAWP"),
    ),
}


def build_report_from_task(
    task: Task,
    reader: StandardsReader,
    *,
    user_request: str = "",
) -> ReportData:
    return _build_workflow_report(task, reader, user_request=user_request)


def build_report_for_task_id(
    task_id: str,
    manager: TaskStateManager,
    reader: StandardsReader,
    *,
    user_request: str = "",
) -> ReportData:
    task = manager.get_task(task_id)
    return build_report_from_task(task, reader, user_request=user_request)


def _resolve_workflow_id(task: Task) -> str:
    return resolve_task_workflow_id(task)


def _missing_inputs_for_report(
    task: Task,
    reader: StandardsReader,
    workflow_id: str,
) -> list[str]:
    if workflow_id:
        return missing_inputs_for_task(task, reader=reader)
    return []


def _build_workflow_report(
    task: Task,
    reader: StandardsReader,
    *,
    user_request: str,
) -> ReportData:
    workflow_id = _resolve_workflow_id(task)
    goal_spec = (
        resolve_root_goal_spec(reader, workflow_id)
        if workflow_id
        else None
    )
    missing = _missing_inputs_for_report(task, reader, workflow_id)
    status = _derive_status(task, missing, goal_spec.target_field if goal_spec else "")

    display_blocks = build_display_outputs(task, reader=reader, standards_root=reader.standards_root)
    display_sections = blocks_to_display_sections(display_blocks)
    input_entries = [_input_entry(key, fact) for key, fact in active_facts(task).items()]

    traversal: list[ReportTraversalStep] = []
    if task.outputs.get("_execution_trace"):
        traversal = _traversal_from_trace(task.outputs["_execution_trace"], reader)
    elif workflow_id:
        traversal = _flatten_traversal(reader, normalize_root_id(workflow_id))

    sections, traceability, formula_display, decisions, limitations = _build_report_sections(
        task,
        reader,
        formula_fallback_node_ids=_equation_node_ids_for_report(task, reader, workflow_id),
        target_field=goal_spec.target_field if goal_spec else "",
    )

    now = datetime.now(timezone.utc).isoformat()
    workflow_title = (
        workflow_display_title_from_node(reader, workflow_id)
        or (goal_spec.title if goal_spec else "")
        or workflow_title_for_goal(reader, workflow_id)
        if workflow_id
        else "Engineering Task"
    )
    request_text = user_request or f"{workflow_title} calculation task"
    documentation = workflow_report_documentation(reader, workflow_id) if workflow_id else {}
    purpose = _report_purpose(
        request_text=request_text,
        workflow_id=workflow_id,
        workflow_title=workflow_title,
        documentation=documentation,
    )
    conclusion = _report_conclusion(
        task=task,
        status=status,
        missing=missing,
        target_field=goal_spec.target_field if goal_spec else "",
    )

    version = ReportVersionInfo(
        report_version="2.0",
        graph_version=workflow_id or "unknown",
        created_date=now,
        task_id=task.task_id,
    )

    return ReportData(
        report_id=f"{task.task_id}-report",
        title=f"{workflow_title} Report" if workflow_title else "Engineering Task Report",
        graph_version=workflow_id or "unknown",
        task_id=task.task_id,
        workflow=workflow_id,
        status=status,
        version_info=version,
        user_request=request_text,
        purpose=purpose,
        standards=["ASME B31.3"] if workflow_id else [],
        input_entries=input_entries,
        traversal=traversal,
        sections=sections,
        traceability=traceability,
        decisions=decisions,
        report_warnings=_report_warnings(task),
        limitations=limitations,
        overrides=_report_overrides(task),
        missing_inputs=missing,
        formula_display=formula_display,
        display_sections=display_sections,
        template_name=resolve_template_name(workflow_id),
        conclusion=conclusion,
    )


def _equation_node_ids_for_report(
    task: Task,
    reader: StandardsReader,
    workflow_id: str,
) -> list[str]:
    if task.outputs.get("_execution_trace"):
        node_ids: list[str] = []
        for entry in task.outputs["_execution_trace"]:
            if isinstance(entry, dict):
                node_id = str(entry.get("node_id", "")).strip()
                if node_id:
                    node_ids.append(node_id)
        if node_ids:
            return node_ids
    if not workflow_id:
        return []
    graph = GraphEngine()
    slug = normalize_root_id(workflow_id)
    preview = graph.build_plan(
        task_id=task.task_id,
        root_id=slug,
        inputs=dict(task.fact_store.active_facts()),
        reader=reader,
    )
    return [
        node_id
        for node_id in preview.execution_order
        if reader.graph_store.node_type(node_id) in {"equation", "calculation", "paragraph"}
    ]


def _build_report_sections(
    task: Task,
    reader: StandardsReader,
    *,
    formula_fallback_node_ids: list[str],
    target_field: str = "",
) -> tuple[
    list[ReportSection],
    list[TraceabilityEntry],
    str | None,
    list[ReportDecision],
    list[str],
]:
    sections: list[ReportSection] = []
    traceability: list[TraceabilityEntry] = []
    formula_display: str | None = None
    decisions: list[ReportDecision] = []
    limitations: list[str] = []

    primary_section: ReportSection | None = None
    primary_trace: TraceabilityEntry | None = None

    for node_id in formula_fallback_node_ids:
        try:
            node = reader.load(node_id)
        except FileNotFoundError:
            continue
        node_type = reader.graph_store.node_type(node_id) or ""
        if node_type not in {"equation", "calculation", "paragraph"}:
            continue
        display = _load_formula_display(reader, node_id)
        if formula_display is None and display:
            formula_display = display
        inputs = {key: fact_scalar_value(fact) for key, fact in active_facts(task).items()}
        outputs = _execution_outputs(task, target_field=target_field)
        section = ReportSection(
            node=node.node_id,
            paragraph=str(node.metadata.get("paragraph", "")),
            source_text=_extract_paragraph_excerpt(node.body),
            formula=display,
            inputs=inputs,
            outputs=outputs,
        )
        trace = TraceabilityEntry(
            node=node.node_id,
            paragraph=str(node.metadata.get("paragraph", "")),
            source_text=_extract_paragraph_excerpt(node.body),
            formula=display,
            inputs=inputs,
            outputs=outputs,
        )
        if primary_section is None:
            primary_section = section
            primary_trace = trace
        conditions = node.metadata.get("conditions", [])
        if isinstance(conditions, list) and conditions:
            first = conditions[0]
            if isinstance(first, dict):
                decisions.append(
                    ReportDecision(
                        node=node.node_id,
                        reason="Applicability must be evaluated before final result selection.",
                        condition=str(first.get("expression", "")),
                        result="recorded at execution" if task.status == TaskStatus.COMPLETED else "pending",
                    )
                )
        limitations.extend(
            str(item.get("condition", item))
            for item in (node.metadata.get("limitations") or [])
            if isinstance(item, dict)
        )
        if formula_display is not None and primary_section is not None:
            break

    if primary_section is not None and primary_trace is not None:
        sections.append(primary_section)
        traceability.append(primary_trace)

    return sections, traceability, formula_display, decisions, limitations


def _report_purpose(
    *,
    request_text: str,
    workflow_id: str,
    workflow_title: str,
    documentation: dict[str, str],
) -> str:
    summary = documentation.get("summary") or documentation.get("report_summary")
    if summary:
        return f"{summary} Design intent: {request_text}."
    workflow_label = workflow_title or workflow_id.replace("_", " ") if workflow_id else "engineering"
    return (
        f"This report summarizes the {workflow_label} task performed for: {request_text}. "
        "It records the design basis, engineering analysis, results, and any warnings relevant "
        "to engineering review."
    )


def _report_conclusion(
    *,
    task: Task,
    status: str,
    missing: list[str],
    target_field: str,
) -> str:
    if missing:
        return (
            "The engineering calculation cannot be finalized. Required design inputs are still "
            f"missing: {', '.join(human_input_label(key) for key in missing)}. "
            "Provide the remaining values and re-run the calculation before issuing this report "
            "for engineering sign-off."
        )
    if status == "INVALIDATED":
        return (
            "The calculation has been invalidated due to input changes or validation failures. "
            "Review the warnings and technical appendix, then re-execute the workflow before "
            "relying on the results."
        )

    output_keys = _GOAL_OUTPUT_KEYS.get(target_field, (target_field,)) if target_field else ()
    for key_group in _GOAL_CONCLUSION_FIELDS.get(target_field, ()):
        if isinstance(key_group, str):
            key_group = (key_group,)
        for key in key_group:
            if task.outputs.get(key) is not None:
                return _goal_value_conclusion(target_field, key, task.outputs)

    for key in output_keys:
        if task.outputs.get(key) is not None:
            return _goal_value_conclusion(target_field, key, task.outputs)

    return _generic_conclusion(task)


def _goal_value_conclusion(target_field: str, output_key: str, outputs: dict[str, Any]) -> str:
    value = outputs.get(output_key)
    if target_field == "minimum_required_thickness":
        if output_key in {"t_m", "minimum_required_thickness"}:
            unit = str(outputs.get("t_m_unit") or outputs.get("minimum_required_thickness_unit") or "mm")
            thickness = format_report_number(value)
            return (
                f"The minimum required pipe wall thickness is {thickness} {unit}. The selected pipe schedule "
                "must provide a nominal wall thickness not less than this value per ASME B31.3 §304.1.1-a. "
                "Refer to the engineering analysis section for the governing equation, substituted "
                "calculation, and schedule recommendation."
            )
        unit = str(outputs.get("required_thickness_unit") or outputs.get("t_unit") or "mm")
        thickness = format_report_number(value)
        return (
            f"The required wall thickness t is {thickness} {unit} per ASME B31.3 §304.1.2. "
            "Minimum required thickness including corrosion allowance should be confirmed before "
            "final pipe selection."
        )
    if target_field == "maximum_allowable_working_pressure":
        unit = str(outputs.get("mawp_unit") or outputs.get("MAWP_unit") or "Pa")
        pressure = format_report_number(value)
        return (
            f"The maximum allowable working pressure (MAWP) is {pressure} {unit} per ASME B31.3 §304.1.2. "
            "Review the engineering analysis section for the governing equation and substituted calculation."
        )
    return (
        f"The calculated {output_key.replace('_', ' ')} is {format_report_number(value)}. "
        "Review the engineering analysis section for supporting calculations."
    )


def _generic_conclusion(task: Task) -> str:
    if task.status == TaskStatus.COMPLETED:
        return "The engineering task completed successfully. Review the results and warnings above."
    if task.status == TaskStatus.INVALIDATED:
        return "The task was invalidated. Review warnings and re-run the workflow before sign-off."
    if task.status == TaskStatus.AWAITING_INPUT:
        return "The task is awaiting additional engineering inputs before results can be finalized."
    return "The task is in progress. This report reflects the current recorded state."


def _execution_outputs(task: Task, *, target_field: str = "") -> dict[str, Any]:
    keys: set[str] = {
        "required_thickness",
        "t",
        "minimum_required_thickness",
        "t_m",
        "allowable_stress",
        "S",
        "mawp",
        "MAWP",
    }
    if target_field:
        keys.update(_GOAL_OUTPUT_KEYS.get(target_field, (target_field,)))
    outputs: dict[str, Any] = {}
    for key in keys:
        if key in task.outputs:
            outputs[key] = task.outputs[key]
    return outputs


def _traversal_from_trace(
    trace: Any,
    reader: StandardsReader | None = None,
) -> list[ReportTraversalStep]:
    if not isinstance(trace, list):
        return []
    steps: list[ReportTraversalStep] = []
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id", ""))
        title = _human_traversal_title(node_id, entry.get("status"), reader)
        steps.append(ReportTraversalStep(node_id=node_id, title=title))
    return steps


def _human_traversal_title(
    node_id: str,
    status: Any,
    reader: StandardsReader | None,
) -> str:
    if reader and node_id:
        try:
            node = reader.load(node_id)
            paragraph = str(node.metadata.get("paragraph", "")).strip()
            node_title = str(node.metadata.get("title", "")).strip()
            if node_title and paragraph:
                return f"{node_title} (§{paragraph})"
            if node_title:
                return node_title
            if paragraph:
                return f"§{paragraph}"
        except FileNotFoundError:
            pass

    status_text = str(status or "").strip()
    if "COMPLETED" in status_text.upper():
        return "Completed"
    if "SKIPPED" in status_text.upper():
        return "Skipped"
    if status_text:
        return status_text.replace("NodeExecutionStatus.", "").replace("_", " ").title()
    return "Executed"


def _derive_status(task: Task, missing: list[str], target_field: str) -> str:
    plan_status = _validation_plan_status(task)
    if plan_status == "FAIL":
        return "INVALIDATED"
    if plan_status == "INCOMPLETE":
        return "INCOMPLETE"
    if task.status == TaskStatus.INVALIDATED:
        return "INVALIDATED"
    if missing:
        return "INCOMPLETE"
    output_keys = _GOAL_OUTPUT_KEYS.get(target_field, ()) if target_field else ()
    if any(task.outputs.get(key) is not None for key in output_keys):
        return "PASS"
    if task.status == TaskStatus.COMPLETED:
        return "PASS"
    return "INCOMPLETE"


def _validation_trace_entries(task: Task) -> list[dict[str, Any]]:
    trace = task.outputs.get("_validation_trace")
    if not isinstance(trace, list):
        return []
    return [entry for entry in trace if isinstance(entry, dict)]


def _validation_plan_status(task: Task) -> str | None:
    for entry in _validation_trace_entries(task):
        if entry.get("scope") == "plan":
            status = entry.get("status")
            return str(status) if status else None
    return None


def _report_warnings(task: Task) -> list[ReportWarning]:
    seen: set[str] = set()
    warnings: list[ReportWarning] = []
    for message in task.warnings:
        if message not in seen:
            seen.add(message)
            warnings.append(ReportWarning(message=message))
    for entry in _validation_trace_entries(task):
        for item in entry.get("warnings", []):
            if not isinstance(item, dict):
                continue
            message = str(item.get("message", ""))
            if message and message not in seen:
                seen.add(message)
                level = str(item.get("severity", "warning"))
                warnings.append(ReportWarning(message=message, level=level))
    return warnings


def _report_overrides(task: Task) -> list[ReportOverride]:
    overrides: list[ReportOverride] = []
    seen: set[tuple[str, str]] = set()
    for entry in _validation_trace_entries(task):
        for item in entry.get("overrides", []):
            if not isinstance(item, dict):
                continue
            rule = str(item.get("rule", ""))
            decision = str(item.get("user_decision", ""))
            key = (rule, decision)
            if rule and key not in seen:
                seen.add(key)
                overrides.append(
                    ReportOverride(
                        rule=rule,
                        original_rule=rule,
                        user_decision=decision,
                        effect=str(item.get("reason") or "User override recorded"),
                    )
                )
    return overrides


def _input_entry(input_id: str, fact: Fact) -> ReportInputEntry:
    original_value = fact.original_value or fact_scalar_value(fact)
    original_unit = fact.original_unit or fact_unit(fact)
    return ReportInputEntry(
        input_id=input_id,
        name=input_id,
        original_value=original_value,
        original_unit=original_unit,
        calculation_value=fact_scalar_value(fact),
        calculation_unit=fact_unit(fact),
    )


def _flatten_traversal(reader: StandardsReader, root_id: str) -> list[ReportTraversalStep]:
    try:
        tree = reader.dependency_tree(root_id)
    except FileNotFoundError:
        return []
    steps: list[ReportTraversalStep] = []

    def walk(node: dict[str, Any]) -> None:
        steps.append(
            ReportTraversalStep(
                node_id=str(node.get("id", "")),
                title=str(node.get("type", "")),
            )
        )
        for child in node.get("children", []):
            if not child.get("cycle"):
                walk(child)

    walk(tree)
    return steps


def _load_formula_display(reader: StandardsReader, node_id: str) -> str | None:
    try:
        node = reader.load(node_id)
    except FileNotFoundError:
        return None
    equations = node.metadata.get("equations", []) or node.metadata.get("formulas", []) or []
    for equation in equations:
        if isinstance(equation, dict) and equation.get("file"):
            path = node.path.parent / str(equation["file"])
            if path.exists():
                text = path.read_text(encoding="utf-8")
                if "display:" in text:
                    for line in text.splitlines():
                        if line.strip().startswith("display:"):
                            return line.split("display:", 1)[1].strip().strip('"')
    display = node.metadata.get("display")
    if display:
        return str(display)
    return None


def _extract_paragraph_excerpt(body: str, limit: int = 400) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith(">"):
            return stripped[:limit]
    return body[:limit].strip()
