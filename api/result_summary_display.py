"""Deterministic result summary display block for the center panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from api.display_block_metadata import tag_display_block
from models.display_role import DisplayRole, ResultKind
from api.flow_guidance_runtime_texts import (
    _runtime_workflow_dirs,
    load_runtime_text_entries,
    result_summary_block_id,
)
from api.flow_guidance_transcript import normalize_workflow_slug
from engine.graph.assumption_checker import field_value
from engine.reference.parameter_keys import param_node_id_for_input
from engine.reference.standards_reader import StandardsReader
from models.task import Task

_WORKFLOWS_ROOT = Path(__file__).resolve().parents[1] / "workflows"


def _load_runtime_metadata(workflow_id: str) -> dict[str, Any]:
    for folder in _runtime_workflow_dirs(workflow_id):
        path = _WORKFLOWS_ROOT / folder / "runtime.yaml"
        if not path.is_file():
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
    return {}


def _runtime_result_narration(workflow_id: str) -> str:
    for entry in load_runtime_text_entries(workflow_id):
        if str(entry.get("role") or "").strip() == "result_explanation":
            text = str(entry.get("text") or "").strip()
            if text:
                return text
    return ""


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
            from engine.reference.parameter_keys import parameter_node_description

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


def _format_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _applied_conditions(task: Task, reader: StandardsReader) -> list[dict[str, str]]:
    conditions: list[dict[str, str]] = []
    seen: set[str] = set()
    facts = task.fact_store.active_facts()

    for fact_key, fact in facts.items():
        key = str(fact_key).strip()
        if not key or key in seen:
            continue
        value = field_value(key, facts)
        if value is None:
            continue
        param_id = param_node_id_for_input(key)
        label = key.replace("_", " ").strip().title()
        if param_id:
            try:
                from engine.reference.parameter_keys import parameter_node_description

                described = parameter_node_description(reader=reader, param_id=param_id)
                if described:
                    label = described
            except (FileNotFoundError, TypeError, ValueError):
                pass
        if isinstance(value, bool):
            if not value:
                continue
            display = label
        else:
            display = f"{label}: {value}"
        if display in seen:
            continue
        seen.add(display)
        conditions.append({"label": display})

    path = task.outputs.get("path_decision") or {}
    if isinstance(path, dict):
        for key, value in path.items():
            if key == "selected_node" or value is None:
                continue
            label = f"{str(key).replace('_', ' ').title()}: {value}"
            if label not in seen:
                seen.add(label)
                conditions.append({"label": label})

    return conditions


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
    warnings = [str(item).strip() for item in (task.warnings or []) if str(item).strip()]
    applied = _applied_conditions(task, reader)
    runtime_narration = _runtime_result_narration(resolved_workflow)

    payload: dict[str, Any] = {
        "display_role": DisplayRole.result_summary.value,
        "result_kind": ResultKind.workflow.value,
        "primary_result": {
            "label": label,
            "value": _format_number(raw_value),
            "unit": unit or None,
            "output_key": goal_key,
        },
        "applied_conditions": applied,
        "warnings": warnings,
    }
    if runtime_narration:
        payload["runtime_narration"] = runtime_narration

    content_lines = [f"{label}: {_format_number(raw_value)}{f' {unit}' if unit else ''}"]
    if applied:
        content_lines.append("")
        content_lines.append("Applied conditions:")
        for item in applied:
            content_lines.append(f"- {item['label']}")
    if warnings:
        content_lines.append("")
        content_lines.append("Warnings / cautions:")
        for warning in warnings:
            content_lines.append(f"- {warning}")
    if runtime_narration:
        content_lines.append("")
        content_lines.append(runtime_narration)

    block_id = result_summary_block_id(resolved_workflow)
    return tag_display_block(
        {
            "id": block_id,
            "type": "text",
            "title": "Result Summary",
            "content": "\n".join(content_lines),
            "variant": "body",
            "payload": payload,
        },
        display_role=DisplayRole.result_summary.value,
    )
