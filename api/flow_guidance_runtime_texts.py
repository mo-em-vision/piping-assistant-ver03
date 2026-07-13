"""Runtime workflow texts and workflow-node transcript blocks for the center panel."""

from __future__ import annotations

from typing import Any

from engine.planner.workflow_goal_metadata import (
    workflow_display_description_from_node,
    workflow_display_title_from_node,
)
from engine.reference.standards_reader import StandardsReader
from models.presentation import PresentationBlock
from models.task import Task, TaskStatus

from api.flow_guidance_transcript import normalize_workflow_slug
from api.workflow_runtime_yaml import load_workflow_runtime_metadata

_RUNTIME_ROLE_TO_DISPLAY = {
    "result_explanation": "result_summary",
}


def workflow_title_block_id(workflow_id: str) -> str:
    return f"workflow-title-{normalize_workflow_slug(workflow_id)}"


def workflow_description_block_id(workflow_id: str) -> str:
    return f"workflow-description-{normalize_workflow_slug(workflow_id)}"


def workflow_intro_block_id(workflow_id: str) -> str:
    """Legacy block id retained for transcript migration tests."""
    return f"workflow-intro-{normalize_workflow_slug(workflow_id)}"


def result_summary_block_id(workflow_id: str) -> str:
    return f"result-summary-{normalize_workflow_slug(workflow_id)}"


def load_runtime_text_entries(workflow_id: str) -> list[dict[str, Any]]:
    """Load ``texts`` entries from workflow runtime metadata."""
    runtime = load_workflow_runtime_metadata(workflow_id)
    texts = runtime.get("texts") or []
    return [item for item in texts if isinstance(item, dict)]


def _format_runtime_text(entry: dict[str, Any]) -> str:
    body = str(entry.get("text") or "").strip()
    title = str(entry.get("title") or "").strip()
    if title and body:
        return f"{title}\n\n{body}"
    return title or body


def load_runtime_documentation_summary(workflow_id: str) -> str:
    """Load workflow initiation summary from runtime documentation block."""
    runtime = load_workflow_runtime_metadata(workflow_id)
    documentation = runtime.get("documentation")
    if isinstance(documentation, dict):
        summary = str(documentation.get("summary") or "").strip()
        if summary:
            return summary
    return ""


def runtime_text_to_presentation_block(
    entry: dict[str, Any],
    workflow_id: str,
) -> PresentationBlock | None:
    role = str(entry.get("role") or "").strip()
    display_role = _RUNTIME_ROLE_TO_DISPLAY.get(role)
    if not display_role:
        return None

    text = _format_runtime_text(entry)
    if not text:
        return None

    title = str(entry.get("title") or "").strip() or None
    block_id = result_summary_block_id(workflow_id)

    payload: dict[str, Any] = {
        "display_role": display_role,
        "runtime_text_id": str(entry.get("id") or "").strip() or None,
    }
    if title:
        payload["title"] = title

    return PresentationBlock(
        block_id=block_id,
        kind="text",
        source="runtime",
        text=text,
        payload={key: value for key, value in payload.items() if value is not None},
    )


def is_runtime_transcript_block(data: dict[str, Any]) -> bool:
    return str(data.get("kind") or "") == "text" and str(data.get("source") or "") == "runtime"


def is_workflow_node_transcript_block(data: dict[str, Any]) -> bool:
    return str(data.get("kind") or "") == "text" and str(data.get("source") or "") == "workflow_node"


def workflow_node_transcript_blocks(
    task: Task,
    reader: StandardsReader,
) -> tuple[PresentationBlock, ...]:
    """Build durable title and description blocks from the workflow node only."""
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()
    if not workflow_id:
        return ()

    blocks: list[PresentationBlock] = []
    title = workflow_display_title_from_node(reader, workflow_id)
    if title:
        blocks.append(
            PresentationBlock(
                block_id=workflow_title_block_id(workflow_id),
                kind="text",
                source="workflow_node",
                text=title,
                payload={"display_role": "title"},
            )
        )

    description = workflow_display_description_from_node(reader, workflow_id)
    if description:
        blocks.append(
            PresentationBlock(
                block_id=workflow_description_block_id(workflow_id),
                kind="text",
                source="workflow_node",
                text=description,
                payload={"display_role": "workflow_description"},
            )
        )

    return tuple(blocks)


def runtime_transcript_candidates(task: Task) -> tuple[PresentationBlock, ...]:
    """Build durable runtime result text blocks for the task transcript."""
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()
    if not workflow_id:
        return ()

    if task.status != TaskStatus.COMPLETED:
        return ()

    blocks: list[PresentationBlock] = []
    for entry in load_runtime_text_entries(workflow_id):
        role = str(entry.get("role") or "").strip()
        if role != "result_explanation":
            continue
        block = runtime_text_to_presentation_block(entry, workflow_id)
        if block is not None:
            blocks.append(block)
    return tuple(blocks)
