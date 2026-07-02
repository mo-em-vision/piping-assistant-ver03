"""Build API-facing authority context summaries."""

from __future__ import annotations

from typing import Any

from models.authority_context import authority_context_to_dict
from models.task import Task


def authority_context_summary(task: Task) -> dict[str, Any] | None:
    auth = task.authority_context
    if auth is None:
        stub_id = task.execution_context.authority_context_id
        if not stub_id:
            return None
        return {
            "id": stub_id,
            "type": "authority_context",
            "task_id": task.task_id,
            "execution_context_id": task.execution_context.id,
            "status": "draft",
            "active_authorities_count": 0,
            "conflicts_count": 0,
            "overrides_count": 0,
        }
    return {
        "id": auth.id,
        "type": auth.type,
        "task_id": auth.task_id,
        "execution_context_id": auth.execution_context_id,
        "status": auth.status.value,
        "active_authorities": [
            {
                "authority_id": a.authority_id,
                "edition": a.edition,
                "role": a.role,
                "status": a.status,
            }
            for a in auth.active_authorities
        ],
        "active_authorities_count": len(auth.active_authorities),
        "applicable_paragraphs_count": len(auth.applicable_paragraphs),
        "applicable_tables_count": len(auth.applicable_tables),
        "conflicts_count": len(auth.conflicts),
        "overrides_count": len(auth.overrides),
        "validation_status": auth.validation.status,
    }


def authority_context_full(task: Task) -> dict[str, Any] | None:
    if task.authority_context is None:
        return None
    return authority_context_to_dict(task.authority_context)
