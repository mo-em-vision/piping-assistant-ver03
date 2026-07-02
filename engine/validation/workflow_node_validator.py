"""Validate workflow knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item

ALLOWED_WORKFLOW_CLASSES = frozenset(
    {
        "design_calculation",
        "verification",
        "inspection",
        "assessment",
        "lookup",
        "selection",
        "reporting",
        "screening",
        "troubleshooting",
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
        "runtime_result",
        "current_phase",
        "active_goal_id",
        "navigation",
        "assumptions",
        "interactions",
        "inputs",
        "equations",
        "nomenclature",
        "conditions",
        "provisional_assumptions",
        "engineering_intent",
        "slug",
        "goal_output",
        "purpose",
        "title",
        "documentation",
        "texts",
        "suggested_workflows",
    }
)


def validate_workflow_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "workflow":
        issues.append("type must be 'workflow'")
    node_id = str(meta.get("id") or "")
    if not node_id.startswith("WF-"):
        issues.append("id must start with 'WF-'")
    if not meta.get("key"):
        issues.append("missing key")
    if not meta.get("name"):
        issues.append("missing name")
    workflow_class = str(meta.get("workflow_class") or "")
    if not workflow_class:
        issues.append("missing workflow_class")
    elif workflow_class not in ALLOWED_WORKFLOW_CLASSES:
        issues.append(f"unknown workflow_class: {workflow_class}")
    if not meta.get("description"):
        issues.append("missing description")
    metadata = meta.get("metadata") or {}
    if not isinstance(metadata, dict) or not metadata.get("status"):
        issues.append("metadata.status required")
    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="workflow", allow_legacy=False)
            )
    return issues
