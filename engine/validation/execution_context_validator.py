"""Validate runtime Execution Context nodes against the template."""

from __future__ import annotations

from typing import Any

from models.execution_context import ExecutionContext, ExecutionContextStatus

_FORBIDDEN_METADATA = frozenset(
    {
        "parameter_definition",
        "concept_definition",
        "dimension_definition",
        "unit_conversion_rule",
        "equation_formula_definition",
        "standard_paragraph_text",
        "authority_text",
        "workflow_definition",
    }
)


def validate_execution_context(ctx: ExecutionContext) -> list[str]:
    issues: list[str] = []
    if ctx.type != "execution_context":
        issues.append("type must be 'execution_context'")
    if not ctx.id:
        issues.append("missing id")
    if not ctx.task_id:
        issues.append("missing task_id")
    if not ctx.workflow_id and ctx.status not in {
        ExecutionContextStatus.NEW,
        ExecutionContextStatus.ACTIVE,
    }:
        issues.append("missing workflow_id for standards-governed execution")

    if ctx.status == ExecutionContextStatus.COMPLETED:
        if ctx.facts_index.conflicting:
            issues.append("completed context cannot have conflicting facts")
        if ctx.state.blocked_goals:
            issues.append("completed context cannot have blocked goals")

    if ctx.workflow_id and not ctx.authority_context_id:
        issues.append("standards-governed execution requires authority_context_id")

    for field in _FORBIDDEN_METADATA:
        if field in (ctx.metadata.__dict__ if ctx.metadata else {}):
            issues.append(f"forbidden metadata field: {field}")

    return issues


def validate_execution_context_dict(data: dict[str, Any]) -> list[str]:
    from models.execution_context import execution_context_from_dict

    return validate_execution_context(execution_context_from_dict(data))
