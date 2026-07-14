"""Deterministic result summary display block for the center panel."""

from __future__ import annotations

from typing import Any

from api.completion_summary_collectors import (
    ASSUMPTIONS_INTRO,
    collect_applied_paragraphs,
    collect_completion_assumptions,
)
from api.display_block_metadata import tag_display_block
from api.flow_guidance_runtime_texts import (
    load_runtime_documentation_summary,
    result_summary_block_id,
)
from api.workflow_runtime_yaml import load_workflow_runtime_metadata
from engine.reference.parameter_keys import (
    load_parameter_node_metadata,
    param_node_id_for_input,
    parameter_node_description,
)
from engine.reference.standards_reader import StandardsReader
from models.display_role import DisplayRole, ResultKind
from models.task import Task


def _load_runtime_metadata(workflow_id: str) -> dict[str, Any]:
    return load_workflow_runtime_metadata(workflow_id)


def _goal_output_key(workflow_id: str) -> str | None:
    meta = _load_runtime_metadata(workflow_id)
    key = str(meta.get("goal_output") or "").strip()
    return key or None


def _resolve_output_label(
    reader: StandardsReader,
    output_key: str,
    *,
    workflow_id: str,
) -> str:
    param_id = param_node_id_for_input(output_key)
    if param_id:
        try:
            label = parameter_node_description(reader=reader, param_id=param_id)
            if label:
                return label
        except (FileNotFoundError, TypeError, ValueError):
            pass
    meta = _load_runtime_metadata(workflow_id)
    report_summary = str((meta.get("documentation") or {}).get("report_summary") or "").strip()
    if report_summary:
        return report_summary
    return output_key.replace("_", " ").strip().title()


def _canonical_symbol(output_key: str) -> str:
    param_id = param_node_id_for_input(output_key)
    if param_id:
        metadata = load_parameter_node_metadata(param_id)
        if metadata is not None:
            symbol = str(metadata.get("canonical_symbol") or "").strip()
            if symbol:
                return symbol
    return output_key


def _format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _assumption_line(assumption: Any) -> str:
    return f"- {assumption.phrase} (according to {assumption.reference_label})"


def _serialize_assumption(assumption: Any) -> dict[str, Any]:
    return {
        "phrase": assumption.phrase,
        "source_node_id": assumption.source_node_id,
        "reference_label": assumption.reference_label,
        "reference_links": [
            {
                "node_id": assumption.source_node_id,
                "label": assumption.reference_label,
            }
        ],
    }


def _serialize_applied_paragraph(paragraph: Any) -> dict[str, Any]:
    return {
        "node_id": paragraph.node_id,
        "label": paragraph.label,
        "authority": paragraph.authority,
        "reference_links": [
            {
                "node_id": paragraph.node_id,
                "label": paragraph.label,
            }
        ],
    }


def build_result_summary_display_block(
    task: Task,
    reader: StandardsReader,
    *,
    workflow_id: str | None = None,
) -> dict[str, Any] | None:
    """Build one structured result summary block from deterministic task state."""
    resolved_workflow = str(workflow_id or task.outputs.get("workflow") or "").strip()
    if not resolved_workflow:
        return None

    goal_key = _goal_output_key(resolved_workflow)
    if not goal_key:
        return None

    raw_value = task.outputs.get(goal_key)
    if raw_value is None:
        for alias in (goal_key, goal_key.upper(), goal_key.lower()):
            if alias in task.outputs and task.outputs[alias] is not None:
                raw_value = task.outputs[alias]
                goal_key = alias
                break
    if raw_value is None:
        return None

    unit = str(
        task.outputs.get(f"{goal_key}_unit")
        or task.outputs.get("minimum_required_thickness_unit")
        or task.outputs.get("t_m_unit")
        or task.outputs.get("t_unit")
        or ""
    ).strip()

    label = _resolve_output_label(reader, goal_key, workflow_id=resolved_workflow)
    symbol = _canonical_symbol(goal_key)
    param_explanation = parameter_node_description(reader=reader, input_id=goal_key)
    documentation_summary = load_runtime_documentation_summary(resolved_workflow)
    warnings = [str(item).strip() for item in (task.warnings or []) if str(item).strip()]

    applied_header, applied_paragraphs = collect_applied_paragraphs(task, reader)
    assumptions = collect_completion_assumptions(task, reader)

    formatted_value = _format_number(raw_value)
    value_line = (
        f"The minimum required wall thickness {symbol} = {formatted_value}{f' {unit}' if unit else ''} "
        "has been calculated."
    )

    content_lines = [value_line]
    if param_explanation:
        content_lines.append("")
        content_lines.append(param_explanation)
    if documentation_summary:
        content_lines.append("")
        content_lines.append(documentation_summary)
    if applied_paragraphs:
        content_lines.append("")
        content_lines.append(applied_header)
        for paragraph in applied_paragraphs:
            content_lines.append(paragraph.label)
    if assumptions:
        content_lines.append("")
        content_lines.append(ASSUMPTIONS_INTRO)
        for assumption in assumptions:
            content_lines.append(_assumption_line(assumption))
    if warnings:
        content_lines.append("")
        content_lines.append("Warnings / cautions:")
        for warning in warnings:
            content_lines.append(f"- {warning}")

    payload: dict[str, Any] = {
        "display_role": DisplayRole.result_summary.value,
        "result_kind": ResultKind.workflow.value,
        "primary_result": {
            "label": label,
            "symbol": symbol,
            "value": formatted_value,
            "unit": unit or None,
            "output_key": goal_key,
        },
        "parameter_explanation": param_explanation or None,
        "documentation_summary": documentation_summary or None,
        "applied_standard_header": applied_header if applied_paragraphs else None,
        "applied_paragraphs": [_serialize_applied_paragraph(item) for item in applied_paragraphs],
        "assumptions_intro": ASSUMPTIONS_INTRO if assumptions else None,
        "assumptions": [_serialize_assumption(item) for item in assumptions],
        "warnings": warnings,
    }

    block_id = result_summary_block_id(resolved_workflow)
    return tag_display_block(
        {
            "id": block_id,
            "type": "result_summary",
            "title": "Result Summary",
            "content": "\n".join(content_lines),
            "variant": "body",
            "payload": payload,
        },
        display_role=DisplayRole.result_summary.value,
    )
