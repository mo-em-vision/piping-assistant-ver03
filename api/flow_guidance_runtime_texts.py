"""Runtime workflow texts and workflow-node transcript blocks for the center panel."""

from __future__ import annotations

from typing import Any

from engine.planner.workflow_goal_metadata import (
    workflow_display_description_from_node,
    workflow_display_title_from_node,
)
from engine.reference.standards_reader import StandardsReader
from models.presentation import PresentationBlock
from models.task import Task

from api.flow_guidance_transcript import normalize_workflow_slug
from api.transcript_projection import combine_workflow_intro_text
from api.workflow_runtime_yaml import load_workflow_runtime_metadata


def workflow_title_block_id(workflow_id: str) -> str:
    return f"workflow-title-{normalize_workflow_slug(workflow_id)}"


def workflow_description_block_id(workflow_id: str) -> str:
    return f"workflow-description-{normalize_workflow_slug(workflow_id)}"


def workflow_intro_block_id(workflow_id: str) -> str:
    return f"workflow-intro-{normalize_workflow_slug(workflow_id)}"


def result_summary_block_id(workflow_id: str) -> str:
    return f"result-summary-{normalize_workflow_slug(workflow_id)}"


def load_runtime_documentation_summary(workflow_id: str) -> str:
    """Load workflow completion summary from runtime documentation block."""
    runtime = load_workflow_runtime_metadata(workflow_id)
    documentation = runtime.get("documentation")
    if isinstance(documentation, dict):
        summary = str(documentation.get("summary") or "").strip()
        if summary:
            return summary
    return ""


def is_legacy_runtime_result_summary_block(block: PresentationBlock) -> bool:
    """True for deprecated transcript-only completion summaries."""
    return (
        block.block_id.startswith("result-summary-")
        and block.kind == "text"
        and block.source == "runtime"
    )


def is_workflow_node_transcript_block(data: dict[str, Any]) -> bool:
    return str(data.get("kind") or "") == "text" and str(data.get("source") or "") == "workflow_node"


def workflow_node_transcript_blocks(
    task: Task,
    reader: StandardsReader,
) -> tuple[PresentationBlock, ...]:
    """Build durable workflow_intro block from the workflow node only."""
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()
    if not workflow_id:
        return ()

    title = workflow_display_title_from_node(reader, workflow_id)
    description = workflow_display_description_from_node(reader, workflow_id)
    if not title and not description:
        return ()

    payload: dict[str, Any] = {"display_role": "workflow_intro"}
    if title:
        payload["title"] = title

    return (
        PresentationBlock(
            block_id=workflow_intro_block_id(workflow_id),
            kind="text",
            source="workflow_node",
            text=combine_workflow_intro_text(title or "", description or ""),
            payload=payload,
        ),
    )
