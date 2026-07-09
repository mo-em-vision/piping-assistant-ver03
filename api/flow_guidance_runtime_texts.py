"""Runtime workflow texts (initiation / result) for durable center-panel transcript."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.reference.workflow_sidecar import _PROJECT_RUNTIME_WORKFLOW_IDS
from models.presentation import PresentationBlock
from models.task import Task, TaskStatus

from api.flow_guidance_transcript import normalize_workflow_slug

_WORKFLOWS_ROOT = Path(__file__).resolve().parents[1] / "workflows"

_RUNTIME_ROLE_TO_DISPLAY = {
    "initiation": "workflow_intro",
    "result_explanation": "result_summary",
}


def workflow_intro_block_id(workflow_id: str) -> str:
    return f"workflow-intro-{normalize_workflow_slug(workflow_id)}"


def result_summary_block_id(workflow_id: str) -> str:
    return f"result-summary-{normalize_workflow_slug(workflow_id)}"


def _runtime_workflow_dirs(workflow_id: str) -> tuple[str, ...]:
    explicit = _PROJECT_RUNTIME_WORKFLOW_IDS.get(workflow_id)
    if explicit:
        return explicit
    return (workflow_id,)


def load_runtime_text_entries(workflow_id: str) -> list[dict[str, Any]]:
    """Load ``texts`` entries from the workflow ``runtime.yaml`` sidecar."""
    for folder in _runtime_workflow_dirs(workflow_id):
        path = _WORKFLOWS_ROOT / folder / "runtime.yaml"
        if not path.is_file():
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return []
        texts = loaded.get("texts") or []
        return [item for item in texts if isinstance(item, dict)]
    return []


def _format_runtime_text(entry: dict[str, Any]) -> str:
    body = str(entry.get("text") or "").strip()
    title = str(entry.get("title") or "").strip()
    if title and body:
        return f"{title}\n\n{body}"
    return title or body


def load_runtime_documentation_summary(workflow_id: str) -> str:
    """Load workflow initiation summary from runtime.yaml documentation block."""
    for folder in _runtime_workflow_dirs(workflow_id):
        path = _WORKFLOWS_ROOT / folder / "runtime.yaml"
        if not path.is_file():
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return ""
        documentation = loaded.get("documentation")
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

    title = str(entry.get("title") or "").strip() or None
    if display_role == "workflow_intro":
        text = load_runtime_documentation_summary(workflow_id) or _format_runtime_text(entry)
    else:
        text = _format_runtime_text(entry)
    if not text:
        return None

    title = str(entry.get("title") or "").strip() or None
    if display_role == "workflow_intro":
        block_id = workflow_intro_block_id(workflow_id)
    else:
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


def runtime_transcript_candidates(task: Task) -> tuple[PresentationBlock, ...]:
    """Build durable runtime text blocks for the task transcript (Phase 1B)."""
    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "").strip()
    if not workflow_id:
        return ()

    include_result = task.status == TaskStatus.COMPLETED
    blocks: list[PresentationBlock] = []
    for entry in load_runtime_text_entries(workflow_id):
        role = str(entry.get("role") or "").strip()
        if role == "result_explanation" and not include_result:
            continue
        block = runtime_text_to_presentation_block(entry, workflow_id)
        if block is not None:
            blocks.append(block)
    return tuple(blocks)
