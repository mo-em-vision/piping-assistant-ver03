"""Migrate task payloads to AuthorityContext v5."""

from __future__ import annotations

from typing import Any

from engine.reference.authority_registry import STANDARD_PRIMARY_AUTHORITY, standard_primary_authority
from engine.state.execution_context_migration import migrate_task_to_v4
from models.authority_context import (
    ActiveAuthority,
    AuthorityContextStatus,
    authority_context_for_execution,
    authority_context_from_dict,
    authority_context_to_dict,
    new_authority_context_id,
)
from models.task import Task


def _authority_from_stub_id(
    task_id: str,
    execution_context_id: str,
    authority_context_id: str,
) -> Any:
    auth = authority_context_for_execution(
        task_id,
        execution_context_id,
        context_id=str(authority_context_id),
        status=AuthorityContextStatus.ACTIVE,
    )
    slug = str(authority_context_id).replace("AUTHCTX-", "")
    standard_key = slug.replace("-", "_")
    if standard_key in STANDARD_PRIMARY_AUTHORITY or slug.replace("-", "_") in STANDARD_PRIMARY_AUTHORITY:
        key = standard_key if standard_key in STANDARD_PRIMARY_AUTHORITY else slug.replace("-", "_")
        authority_id, edition, role = standard_primary_authority(key)
        auth.active_authorities = [
            ActiveAuthority(authority_id=authority_id, edition=edition, role=role)
        ]
    elif slug:
        parts = slug.upper().split("-")
        auth.active_authorities = [
            ActiveAuthority(
                authority_id=f"AUTH-{'-'.join(parts)}",
                role="primary_design_code",
            )
        ]
    return auth


def migrate_task_to_v5(data: dict[str, Any]) -> dict[str, Any]:
    """Return task dict with authority_context for payload_version 5."""
    migrated = migrate_task_to_v4(data)
    version = int(migrated.get("payload_version", 4))

    if version >= 5 and migrated.get("authority_context"):
        migrated["payload_version"] = 5
        return migrated

    task_id = str(migrated["task_id"])
    exec_ctx = migrated.get("execution_context") or {}
    execution_context_id = str(exec_ctx.get("id") or "")
    authority_context_id = exec_ctx.get("authority_context_id")

    if migrated.get("authority_context"):
        auth = authority_context_from_dict(migrated["authority_context"])
    elif authority_context_id:
        auth = _authority_from_stub_id(task_id, execution_context_id, str(authority_context_id))
    else:
        auth = None

    result = dict(migrated)
    result["payload_version"] = 5
    if auth is not None:
        if not auth.id:
            auth.id = new_authority_context_id()
        result["authority_context"] = authority_context_to_dict(auth)
        if isinstance(exec_ctx, dict):
            exec_ctx["authority_context_id"] = auth.id
            result["execution_context"] = exec_ctx
    return result


def wrap_task_authority_context(task: Task) -> Task:
    """Ensure v5 task has authority_context linked when stub ID exists."""
    if task.payload_version >= 5 and task.authority_context is not None:
        return task
    stub_id = task.execution_context.authority_context_id
    if stub_id and task.authority_context is None:
        task.authority_context = _authority_from_stub_id(
            task.task_id,
            task.execution_context.id,
            stub_id,
        )
    return task
