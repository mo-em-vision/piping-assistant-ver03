"""Completion-time durable next_workflows blocks for flow_guidance transcript."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_reader import StandardsReader
from engine.reference.workflow_sidecar import _PROJECT_RUNTIME_WORKFLOW_IDS
from models.presentation import PresentationBlock
from models.task import Task, TaskStatus

from api.flow_guidance_transcript import (
    load_flow_guidance_transcript_blocks,
    merge_append_only_blocks,
    normalize_workflow_slug,
    save_flow_guidance_transcript,
)

_WORKFLOWS_ROOT = Path(__file__).resolve().parents[1] / "workflows"
_NEXT_WORKFLOWS_TITLE = "Suggested next workflows"
_NEXT_WORKFLOWS_INTRO = "Based on this workflow, you may continue with:"


def _runtime_workflow_dirs(workflow_id: str) -> tuple[str, ...]:
    explicit = _PROJECT_RUNTIME_WORKFLOW_IDS.get(workflow_id)
    if explicit:
        return explicit
    return (workflow_id,)


def next_workflows_block_id(task_id: str, workflow_id: str) -> str:
    task_slug = normalize_workflow_slug(task_id)
    workflow_slug = normalize_workflow_slug(workflow_id)
    return f"next-workflows-{task_slug}-{workflow_slug}"


def is_next_workflows_block(data: dict[str, Any]) -> bool:
    return (
        str(data.get("kind") or "") == "next_workflows"
        and str(data.get("source") or "") == "workflow_runtime"
    )


def load_runtime_suggested_workflow_ids(workflow_id: str) -> list[str]:
    """Read suggested_workflows slugs from workflow runtime.yaml."""
    workflow_id = str(workflow_id or "").strip()
    if not workflow_id:
        return []

    for folder in _runtime_workflow_dirs(workflow_id):
        path = _WORKFLOWS_ROOT / folder / "runtime.yaml"
        if not path.is_file():
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return []
        suggested = loaded.get("suggested_workflows") or []
        if not isinstance(suggested, list):
            return []
        return [str(item).strip() for item in suggested if str(item).strip()]
    return []


def _workflow_id_for_task(task: Task) -> str:
    return str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()


def _catalog_entry(workflow_id: str, reader: StandardsReader) -> dict[str, Any]:
    from api.serializers import workflow_catalog

    for item in workflow_catalog(reader):
        if item.get("id") == workflow_id or item.get("node_id") == workflow_id:
            return dict(item)
    return {
        "id": workflow_id,
        "name": workflow_id.replace("_", " ").title(),
        "description": "",
        "available": False,
    }


def resolve_next_workflow_suggestions(
    suggested_ids: list[str],
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for workflow_id in suggested_ids:
        workflow_id = str(workflow_id or "").strip()
        if not workflow_id:
            continue
        meta = _catalog_entry(workflow_id, reader)
        available = bool(meta.get("available", False))
        item: dict[str, Any] = {
            "workflow_id": workflow_id,
            "title": str(meta.get("name") or workflow_id),
            "available": available,
        }
        description = str(meta.get("description") or "").strip()
        if description:
            item["description"] = description
        if available:
            item["action"] = {"type": "start_workflow", "workflow_id": workflow_id}
        suggestions.append(item)
    return suggestions


def build_next_workflows_block(task: Task, reader: StandardsReader) -> PresentationBlock | None:
    """Build one completion next_workflows transcript block, or None when no suggestions."""
    workflow_id = _workflow_id_for_task(task)
    if not workflow_id:
        return None

    suggested_ids = load_runtime_suggested_workflow_ids(workflow_id)
    suggestions = resolve_next_workflow_suggestions(suggested_ids, reader)
    if not suggestions:
        return None

    block_id = next_workflows_block_id(task.task_id, workflow_id)
    return PresentationBlock(
        block_id=block_id,
        kind="next_workflows",
        source="workflow_runtime",
        text=_NEXT_WORKFLOWS_INTRO,
        payload={
            "display_role": "next_workflows",
            "workflow_id": workflow_id,
            "title": _NEXT_WORKFLOWS_TITLE,
            "suggestions": suggestions,
        },
    )


def transcript_block_to_api_dict(block: PresentationBlock) -> dict[str, Any]:
    """Flatten presentation blocks for API consumers."""
    if block.kind != "next_workflows":
        return block.to_dict()

    payload = dict(block.payload or {})
    flattened: dict[str, Any] = {
        "block_id": block.block_id,
        "kind": block.kind,
        "source": block.source,
        "display_role": payload.get("display_role", "next_workflows"),
        "workflow_id": payload.get("workflow_id"),
        "title": payload.get("title", _NEXT_WORKFLOWS_TITLE),
        "text": block.text,
        "suggestions": list(payload.get("suggestions") or []),
    }
    return {key: value for key, value in flattened.items() if value is not None}


def flatten_transcript_blocks_for_api(
    blocks: tuple[PresentationBlock, ...],
) -> list[dict[str, Any]]:
    return [transcript_block_to_api_dict(block) for block in blocks]


def _transcript_has_next_workflows_block(
    stored: tuple[PresentationBlock, ...],
    block_id: str,
) -> bool:
    return any(block.block_id == block_id for block in stored)


def append_completion_next_workflows_transcript(
    task: Task,
    reader: StandardsReader,
) -> tuple[Task, bool]:
    """Append one next_workflows block when task is completed (idempotent)."""
    if task.status != TaskStatus.COMPLETED:
        return task, False

    block = build_next_workflows_block(task, reader)
    if block is None:
        return task, False

    stored = load_flow_guidance_transcript_blocks(task)
    if _transcript_has_next_workflows_block(stored, block.block_id):
        return task, False

    merged, changed = merge_append_only_blocks(stored, (block,))
    if not changed:
        return task, False

    save_flow_guidance_transcript(task, merged)
    return task, True


def maybe_repair_completion_next_workflows_transcript(
    task: Task,
    reader: StandardsReader,
) -> tuple[Task, bool]:
    """Idempotent repair: append missing next_workflows block for completed tasks."""
    return append_completion_next_workflows_transcript(task, reader)
