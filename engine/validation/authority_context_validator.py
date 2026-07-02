"""Validate runtime Authority Context nodes against the template."""

from __future__ import annotations

from typing import Any

from models.authority_context import (
    AuthorityContext,
    AuthorityContextStatus,
)

_FORBIDDEN_FIELDS = frozenset(
    {
        "calculation_result",
        "fact_value",
        "unit_conversion_rule",
        "parameter_definition",
        "concept_definition",
        "equation_formula",
        "full_standard_text",
    }
)


def validate_authority_context(ctx: AuthorityContext) -> list[str]:
    issues: list[str] = []
    if ctx.type != "authority_context":
        issues.append("type must be 'authority_context'")
    if not ctx.id:
        issues.append("missing id")
    if not ctx.task_id:
        issues.append("missing task_id")
    if not ctx.execution_context_id:
        issues.append("missing execution_context_id")

    active_statuses = {
        AuthorityContextStatus.ACTIVE,
        AuthorityContextStatus.VALIDATED,
    }
    if ctx.status in active_statuses and not ctx.active_authorities:
        issues.append("active authority context requires at least one active_authority")

    unresolved = [
        c for c in ctx.conflicts
        if c.resolution.status not in {"resolved", "accepted"}
    ]
    if ctx.status == AuthorityContextStatus.VALIDATED and unresolved:
        issues.append("validated context cannot have unresolved conflicts")

    for override in ctx.overrides:
        if not override.reason:
            issues.append(f"override {override.id} requires reason")

    active_authority_ids = {a.authority_id for a in ctx.active_authorities if a.status == "active"}
    for active in ctx.active_authorities:
        if not str(active.authority_id).startswith("AUTH-"):
            issues.append(f"active authority id must start with AUTH-: {active.authority_id}")
    for paragraph in ctx.applicable_paragraphs:
        if not _paragraph_has_active_parent(paragraph, active_authority_ids):
            issues.append(f"paragraph {paragraph} parent authority is not active")

    for table in ctx.applicable_tables:
        if not _table_has_active_parent(table, active_authority_ids):
            issues.append(f"table {table} parent authority is not active")

    return issues


def validate_authority_context_dict(data: dict[str, Any]) -> list[str]:
    from models.authority_context import authority_context_from_dict

    issues = validate_authority_context(authority_context_from_dict(data))
    for field in _FORBIDDEN_FIELDS:
        if field in data:
            issues.append(f"forbidden field: {field}")
    return issues


def _paragraph_has_active_parent(paragraph_id: str, active_ids: set[str]) -> bool:
    if not active_ids:
        return False
    upper = paragraph_id.upper()
    for authority_id in active_ids:
        token = authority_id.replace("AUTH-", "").replace("-", "").upper()
        if token and token[:4] in upper:
            return True
    return bool(active_ids)


def _table_has_active_parent(table_id: str, active_ids: set[str]) -> bool:
    if not active_ids:
        return False
    upper = table_id.upper()
    for authority_id in active_ids:
        token = authority_id.replace("AUTH-", "").replace("-", "").upper()
        if token and token[:4] in upper:
            return True
    return bool(active_ids)
