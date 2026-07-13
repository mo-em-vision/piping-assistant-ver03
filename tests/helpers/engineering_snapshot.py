"""Helpers for comparing engineering truth before/after presentation layers."""

from __future__ import annotations

import json
from typing import Any

from api.output_blocks import build_display_outputs
from engine.reference.standards_reader import StandardsReader
from models.task import Task

_ENGINEERING_OUTPUT_KEYS = (
    "t",
    "t_m",
    "required_thickness",
    "minimum_required_thickness",
    "allowable_stress",
    "S",
    "thin_wall",
    "workflow",
    "selected_root",
)


def engineering_truth_snapshot(task: Task, reader: StandardsReader) -> dict[str, Any]:
    """Capture task facts/outputs/warnings and trace-backed display blocks."""
    return {
        "outputs": {
            key: task.outputs.get(key)
            for key in _ENGINEERING_OUTPUT_KEYS
            if key in task.outputs
        },
        "facts": {
            key: fact.value for key, fact in sorted(task.fact_store.active_facts().items())
        },
        "warnings": list(task.warnings),
        "display_outputs": normalize_display_outputs(
            build_display_outputs(task, reader=reader, standards_root=reader.standards_root)
        ),
    }


def normalize_display_outputs(blocks: list[dict[str, Any]]) -> str:
    """Stable JSON snapshot of user-visible engineering display blocks."""
    normalized: list[dict[str, Any]] = []
    for block in blocks:
        block_type = str(block.get("type") or "")
        item: dict[str, Any] = {
            "id": block.get("id"),
            "type": block_type,
            "node_id": block.get("node_id"),
        }
        if block_type in {"equation_evaluation", "equation_trace"}:
            item["substituted_latex"] = block.get("substituted_latex")
            item["symbolic_latex"] = block.get("symbolic_latex")
            item["result"] = block.get("result")
            item["input_table"] = block.get("input_table")
            item["intermediate_values"] = block.get("intermediate_values")
        elif block_type == "warning":
            item["text"] = block.get("text")
        elif block_type == "lookup_result":
            item["lookup_id"] = block.get("lookup_id")
            item["value"] = block.get("value")
            item["unit"] = block.get("unit")
            item["table"] = block.get("table")
        elif block_type == "result_summary":
            item["value"] = block.get("value")
            item["unit"] = block.get("unit")
            item["label"] = block.get("label")
        normalized.append(item)
    return json.dumps(normalized, sort_keys=True, default=str)
