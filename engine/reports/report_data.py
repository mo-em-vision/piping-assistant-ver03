"""Build ReportData from task state and standards knowledge."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from api.output_blocks import build_display_outputs
from engine.reports.number_format import format_report_number
from engine.reference.standards_reader import StandardsReader
from engine.reports.block_renderer import blocks_to_display_sections, human_input_label
from engine.reports.template_registry import PIPE_WALL_THICKNESS_WORKFLOW, resolve_template_name
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

ROOT_SLUG = "pipe_wall_thickness_design"
WALL_THICKNESS_NODE = "B313-304.1.2"

REQUIRED_INPUTS = ("design_pressure", "outside_diameter", "material", "design_temperature")


def build_report_from_task(
    task: Task,
    reader: StandardsReader,
    *,
    user_request: str = "",
) -> ReportData:
    if _task_is_wall_thickness(task):
        return _build_pipe_wall_thickness_report(task, reader, user_request=user_request)
    return _build_generic_report(task, reader, user_request=user_request)


def build_report_for_task_id(
    task_id: str,
    manager: TaskStateManager,
    reader: StandardsReader,
    *,
    user_request: str = "",
) -> ReportData:
    task = manager.get_task(task_id)
    return build_report_from_task(task, reader, user_request=user_request)


def _task_is_wall_thickness(task: Task) -> bool:
    if task.outputs.get("workflow") == PIPE_WALL_THICKNESS_WORKFLOW:
        return True
    normalized = task.task_id.replace("-", "_")
    return PIPE_WALL_THICKNESS_WORKFLOW in normalized


def _build_pipe_wall_thickness_report(
    task: Task,
    reader: StandardsReader,
    *,
    user_request: str,
) -> ReportData:
    root = reader.load(ROOT_SLUG)
    node = reader.load(WALL_THICKNESS_NODE)
    missing = [key for key in REQUIRED_INPUTS if key not in active_facts(task)]
    status = _derive_status(task, missing)

    traversal = _flatten_traversal(reader, ROOT_SLUG)
    input_entries = [_input_entry(key, fact) for key, fact in active_facts(task).items()]
    formula_display = _load_formula_display(reader, WALL_THICKNESS_NODE)
    display_blocks = build_display_outputs(task, reader=reader, standards_root=reader.standards_root)
    display_sections = blocks_to_display_sections(display_blocks)

    section = ReportSection(
        node=node.node_id,
        paragraph=str(node.metadata.get("paragraph", "")),
        source_text=_extract_paragraph_excerpt(node.body),
        formula=formula_display,
        inputs={key: fact_scalar_value(fact) for key, fact in active_facts(task).items()},
        outputs=_execution_outputs(task),
    )

    trace = TraceabilityEntry(
        node=node.node_id,
        paragraph=str(node.metadata.get("paragraph", "")),
        source_text=_extract_paragraph_excerpt(node.body),
        formula=formula_display,
        inputs=section.inputs,
        outputs=section.outputs,
    )

    if task.outputs.get("_execution_trace"):
        traversal = _traversal_from_trace(task.outputs["_execution_trace"], reader)

    thin_wall = node.metadata.get("conditions", [])
    decisions: list[ReportDecision] = []
    if thin_wall and isinstance(thin_wall, list) and thin_wall:
        first = thin_wall[0]
        if isinstance(first, dict):
            decisions.append(
                ReportDecision(
                    node=node.node_id,
                    reason="Thin-wall applicability must be evaluated before final thickness selection.",
                    condition=str(first.get("expression", "")),
                    result="pending" if missing else "recorded at execution",
                )
            )

    limitations = [
        str(item.get("condition", item))
        for item in (node.metadata.get("limitations") or [])
        if isinstance(item, dict)
    ]

    now = datetime.now(timezone.utc).isoformat()
    version = ReportVersionInfo(
        report_version="2.0",
        graph_version=PIPE_WALL_THICKNESS_WORKFLOW,
        node_versions={
            root.node_id: str(root.metadata.get("version", "1.0")),
            node.node_id: str(node.metadata.get("version", "1.0")),
        },
        created_date=now,
        task_id=task.task_id,
    )

    request_text = user_request or "Pipe wall thickness design / verification"
    purpose = _pipe_wall_purpose(request_text)
    conclusion = _pipe_wall_conclusion(status, missing, task.outputs)

    return ReportData(
        report_id=f"{task.task_id}-report",
        title="Pipe Wall Thickness Design Report",
        graph_version=PIPE_WALL_THICKNESS_WORKFLOW,
        task_id=task.task_id,
        workflow=PIPE_WALL_THICKNESS_WORKFLOW,
        status=status,
        version_info=version,
        user_request=request_text,
        purpose=purpose,
        standards=["ASME B31.3"],
        input_entries=input_entries,
        traversal=traversal,
        sections=[section],
        traceability=[trace],
        decisions=decisions,
        report_warnings=_report_warnings(task),
        limitations=limitations,
        overrides=_report_overrides(task),
        missing_inputs=missing,
        formula_display=formula_display,
        display_sections=display_sections,
        template_name=resolve_template_name(PIPE_WALL_THICKNESS_WORKFLOW),
        conclusion=conclusion,
    )


def _build_generic_report(
    task: Task,
    reader: StandardsReader,
    *,
    user_request: str,
) -> ReportData:
    workflow = str(task.outputs.get("workflow") or "")
    display_blocks = build_display_outputs(task, reader=reader, standards_root=reader.standards_root)
    display_sections = blocks_to_display_sections(display_blocks)
    now = datetime.now(timezone.utc).isoformat()
    request_text = user_request or "Engineering calculation task"
    return ReportData(
        report_id=f"{task.task_id}-report",
        title="Engineering Task Report",
        graph_version=workflow or "unknown",
        task_id=task.task_id,
        workflow=workflow,
        status=task.status.value.upper(),
        version_info=ReportVersionInfo(
            created_date=now,
            task_id=task.task_id,
        ),
        user_request=request_text,
        purpose=_generic_purpose(request_text, workflow),
        report_warnings=_report_warnings(task),
        overrides=_report_overrides(task),
        display_sections=display_sections,
        template_name=resolve_template_name(workflow),
        conclusion=_generic_conclusion(task),
    )


def _pipe_wall_purpose(user_request: str) -> str:
    return (
        "This report documents the pressure design evaluation for straight pipe under internal "
        "pressure in accordance with ASME B31.3 §304.1.2. It presents the design basis, governing "
        "equation, substituted calculation, applicability checks, and minimum required wall thickness "
        f"for the stated design intent: {user_request}."
    )


def _generic_purpose(user_request: str, workflow: str) -> str:
    workflow_label = workflow.replace("_", " ") if workflow else "engineering"
    return (
        f"This report summarizes the {workflow_label} task performed for: {user_request}. "
        "It records the design basis, engineering analysis, results, and any warnings relevant "
        "to engineering review."
    )


def _pipe_wall_conclusion(status: str, missing: list[str], outputs: dict[str, Any]) -> str:
    if missing:
        return (
            "The wall thickness design cannot be finalized. Required design inputs are still "
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
    t_m = outputs.get("t_m") or outputs.get("minimum_required_thickness")
    required = outputs.get("required_thickness") or outputs.get("t")
    if t_m is not None:
        unit = str(outputs.get("t_m_unit") or outputs.get("minimum_required_thickness_unit") or "mm")
        thickness = format_report_number(t_m)
        return (
            f"The minimum required pipe wall thickness is {thickness} {unit}. The selected pipe schedule "
            "must provide a nominal wall thickness not less than this value per ASME B31.3 §304.1.1(a). "
            "Refer to the engineering analysis section for the governing equation, substituted "
            "calculation, and schedule recommendation."
        )
    if required is not None:
        unit = str(outputs.get("required_thickness_unit") or outputs.get("t_unit") or "mm")
        thickness = format_report_number(required)
        return (
            f"The required wall thickness t is {thickness} {unit} per ASME B31.3 §304.1.2. "
            "Minimum required thickness including corrosion allowance should be confirmed before "
            "final pipe selection."
        )
    return (
        "Design inputs have been recorded. Complete the calculation workflow to obtain required "
        "thickness and minimum required thickness values for final engineering review."
    )


def _generic_conclusion(task: Task) -> str:
    if task.status == TaskStatus.COMPLETED:
        return "The engineering task completed successfully. Review the results and warnings above."
    if task.status == TaskStatus.INVALIDATED:
        return "The task was invalidated. Review warnings and re-run the workflow before sign-off."
    if task.status == TaskStatus.AWAITING_INPUT:
        return "The task is awaiting additional engineering inputs before results can be finalized."
    return "The task is in progress. This report reflects the current recorded state."


def _execution_outputs(task: Task) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for key in (
        "required_thickness",
        "t",
        "minimum_required_thickness",
        "t_m",
        "allowable_stress",
        "S",
    ):
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


def _derive_status(task: Task, missing: list[str]) -> str:
    plan_status = _validation_plan_status(task)
    if plan_status == "FAIL":
        return "INVALIDATED"
    if plan_status == "INCOMPLETE":
        return "INCOMPLETE"
    if task.status == TaskStatus.INVALIDATED:
        return "INVALIDATED"
    if missing:
        return "INCOMPLETE"
    if task.outputs.get("required_thickness") or task.outputs.get("t"):
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
    tree = reader.dependency_tree(root_id)
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
    node = reader.load(node_id)
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
    return "t = PD / 2(SEW + PY)"


def _extract_paragraph_excerpt(body: str, limit: int = 400) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith(">"):
            return stripped[:limit]
    return body[:limit].strip()
