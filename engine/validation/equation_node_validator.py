"""Validate equation knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item

ALLOWED_EQUATION_CLASSES = frozenset(
    {
        "calculation",
        "lookup",
        "condition",
        "validation",
        "selection",
        "aggregation",
        "comparison",
        "transformation",
    }
)

ALLOWED_CALCULATION_KINDS = frozenset(
    {
        "algebraic",
        "lookup_table",
        "piecewise",
        "conditional",
        "iterative",
        "function",
        "boolean",
        "comparison",
    }
)

_FORBIDDEN_FIELDS = frozenset(
    {
        "runtime_value",
        "fact_value",
        "user_input",
        "execution_id",
        "task_id",
        "calculation_result",
        "selected_for_execution",
        "active_in_context",
        "variables",
        "steps",
        "executor",
        "execution_function",
        "calculation_module",
        "outputs",
        "equation_id",
    }
)


def validate_equation_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "equation":
        issues.append("type must be 'equation'")
    node_id = str(meta.get("id") or "")
    if not node_id.startswith("asme_"):
        issues.append("id must start with 'asme_' for standards-pack equations")
    if not meta.get("key"):
        issues.append("missing key")
    if not meta.get("name"):
        issues.append("missing name")
    equation_class = str(meta.get("equation_class") or "")
    if not equation_class:
        issues.append("missing equation_class")
    elif equation_class not in ALLOWED_EQUATION_CLASSES:
        issues.append(f"unknown equation_class: {equation_class}")
    calc_kind = str(meta.get("calculation_kind") or "")
    if calc_kind and calc_kind not in ALLOWED_CALCULATION_KINDS:
        issues.append(f"unknown calculation_kind: {calc_kind}")
    if not meta.get("description"):
        issues.append("missing description")
    authority = meta.get("authority") or {}
    if isinstance(authority, dict):
        authorized = authority.get("authorized_by") or []
        if not authorized:
            issues.append("authority.authorized_by required")
    else:
        issues.append("authority block required")
    requires = meta.get("requires")
    calculates = meta.get("calculates")
    if requires is None and calculates is None:
        issues.append("requires or calculates required")
    metadata = meta.get("metadata") or {}
    if not isinstance(metadata, dict):
        issues.append("metadata must be a dict")
    elif not metadata.get("status"):
        issues.append("metadata.status required")
    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="equation", allow_legacy=False)
            )
    return issues
