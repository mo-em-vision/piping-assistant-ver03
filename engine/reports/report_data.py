"""Build ReportData from task state and standards knowledge."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
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

PIPE_WALL_THICKNESS_WORKFLOW = "pipe_wall_thickness_design"
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
    missing = [key for key in REQUIRED_INPUTS if key not in task.inputs]
    status = _derive_status(task, missing)

    traversal = _flatten_traversal(reader, ROOT_SLUG)
    input_entries = [_input_entry(key, task.inputs[key]) for key in task.inputs]
    formula_display = _load_formula_display(reader, WALL_THICKNESS_NODE)

    section = ReportSection(
        node=node.node_id,
        paragraph=str(node.metadata.get("paragraph", "")),
        source_text=_extract_paragraph_excerpt(node.body),
        formula=formula_display,
        inputs={key: inp.value for key, inp in task.inputs.items()},
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
        traversal = _traversal_from_trace(task.outputs["_execution_trace"])

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
        report_version="1.0",
        graph_version=PIPE_WALL_THICKNESS_WORKFLOW,
        node_versions={
            root.node_id: str(root.metadata.get("version", "1.0")),
            node.node_id: str(node.metadata.get("version", "1.0")),
        },
        created_date=now,
        task_id=task.task_id,
    )

    return ReportData(
        report_id=f"{task.task_id}-report",
        title="Pipe Wall Thickness Design Report",
        graph_version=PIPE_WALL_THICKNESS_WORKFLOW,
        task_id=task.task_id,
        workflow=PIPE_WALL_THICKNESS_WORKFLOW,
        status=status,
        version_info=version,
        user_request=user_request or "Pipe wall thickness design / verification",
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
        conclusion=_conclusion(status, missing, task.outputs),
    )


def _build_generic_report(
    task: Task,
    reader: StandardsReader,
    *,
    user_request: str,
) -> ReportData:
    now = datetime.now(timezone.utc).isoformat()
    return ReportData(
        report_id=f"{task.task_id}-report",
        title=f"Engineering Task Report — {task.task_id}",
        graph_version="unknown",
        task_id=task.task_id,
        status=task.status.value.upper(),
        version_info=ReportVersionInfo(
            created_date=now,
            task_id=task.task_id,
        ),
        user_request=user_request,
        report_warnings=_report_warnings(task),
        overrides=_report_overrides(task),
        conclusion="Generic report shell — workflow-specific builder not available.",
    )


def _execution_outputs(task: Task) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for key in ("required_thickness", "t", "allowable_stress", "S"):
        if key in task.outputs:
            outputs[key] = task.outputs[key]
    return outputs


def _traversal_from_trace(trace: Any) -> list[ReportTraversalStep]:
    if not isinstance(trace, list):
        return []
    steps: list[ReportTraversalStep] = []
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        steps.append(
            ReportTraversalStep(
                node_id=str(entry.get("node_id", "")),
                title=str(entry.get("status", "")),
            )
        )
    return steps


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


def _input_entry(input_id: str, engineering_input: Any) -> ReportInputEntry:
    symbol = input_id
    original_value = engineering_input.original_value or engineering_input.value
    original_unit = engineering_input.original_unit or engineering_input.unit
    return ReportInputEntry(
        input_id=input_id,
        name=symbol,
        original_value=original_value,
        original_unit=original_unit,
        calculation_value=engineering_input.value,
        calculation_unit=engineering_input.unit,
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


def _conclusion(status: str, missing: list[str], outputs: dict[str, Any]) -> str:
    if missing:
        return (
            f"Report is incomplete. Missing inputs: {', '.join(missing)}. "
            "Calculations cannot be finalized until all required values are provided."
        )
    if outputs.get("required_thickness") or outputs.get("t"):
        return "Required thickness has been recorded in the execution outputs."
    return "Task data collected; full calculation trace pending engine execution."
