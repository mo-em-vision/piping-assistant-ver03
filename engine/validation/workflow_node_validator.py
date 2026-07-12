"""Validate workflow knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.reference.workflow_authoring_policy import validator_fail_messages_for_workflow
from engine.validation.node_revision_metadata import validate_revision_metadata

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
    issues.extend(validate_revision_metadata(meta))
    issues.extend(validator_fail_messages_for_workflow(meta))
    issues.extend(validate_no_links_metadata(meta))
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="workflow", allow_legacy=False)
            )
    return issues
