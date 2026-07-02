"""Build and link runtime AuthorityContext on tasks."""

from __future__ import annotations

from datetime import datetime, timezone

from engine.reference.authority_registry import standard_primary_authority
from engine.reference.standards_reader import StandardsReader
from models.authority_context import (
    ActiveAuthority,
    AuthorityContext,
    AuthorityContextStatus,
    authority_context_for_execution,
    new_authority_context_id,
)
from models.task import Task


def build_authority_context(
    task: Task,
    reader: StandardsReader | None = None,
    workflow_id: str | None = None,
) -> AuthorityContext:
    """Create or refresh AuthorityContext from the active workflow standard."""
    wf = workflow_id or str(
        task.outputs.get("workflow") or task.execution_context.workflow_id or ""
    )
    ctx = task.execution_context
    standard = "asme_b31.3"
    if reader is not None:
        standard = str(getattr(reader, "standard", standard) or standard)
    standard_slug = standard.replace("_", "-")

    if task.authority_context is None:
        auth_id = new_authority_context_id(standard_slug=standard_slug)
        task.authority_context = authority_context_for_execution(
            task.task_id,
            ctx.id,
            context_id=auth_id,
            status=AuthorityContextStatus.DRAFT if not wf else AuthorityContextStatus.ACTIVE,
        )
    else:
        task.authority_context.task_id = task.task_id
        task.authority_context.execution_context_id = ctx.id

    auth = task.authority_context
    if wf and not auth.active_authorities:
        authority_id, edition, role = standard_primary_authority(standard)
        auth.active_authorities = [
            ActiveAuthority(authority_id=authority_id, edition=edition, role=role)
        ]
        auth.status = AuthorityContextStatus.ACTIVE

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if auth.metadata.created is None:
        auth.metadata.created = now
    auth.metadata.modified = now

    link_authority_context(task)
    return auth


def link_authority_context(task: Task) -> None:
    """Sync bidirectional IDs between execution and authority contexts."""
    if task.authority_context is None:
        return
    task.execution_context.authority_context_id = task.authority_context.id
    task.authority_context.execution_context_id = task.execution_context.id
    task.authority_context.task_id = task.task_id


def ensure_authority_context_for_task(
    task: Task,
    reader: StandardsReader | None = None,
    workflow_id: str | None = None,
) -> None:
    """Ensure task has a linked authority context when a workflow is active."""
    wf = workflow_id or str(
        task.outputs.get("workflow") or task.execution_context.workflow_id or ""
    )
    if not wf and task.execution_context.authority_context_id:
        return
    if not wf:
        return
    build_authority_context(task, reader=reader, workflow_id=wf)
