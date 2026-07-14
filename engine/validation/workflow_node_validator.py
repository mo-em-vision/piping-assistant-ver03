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


_FORBIDDEN_WORKFLOW_ANCHOR_EDGES = frozenset({"starts_from_parameter", "starts_from_paragraph"})
_EXPECTED_COMPLETION_WHEN = "target_parameter_satisfied"
_EXPECTED_COMPLETION_STATUS = "finished"


def _definition_anchor_entry(meta: dict[str, Any]) -> dict[str, Any] | None:
    for entry in meta.get("entry_points") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("role") or "") == "definition_anchor":
            return entry
    return None


def validate_workflow_goal_anchor(meta: dict[str, Any]) -> list[str]:
    """Validate goal anchor and completion metadata on workflow nodes."""
    issues: list[str] = []
    root_goal_cfg = {}
    goal_expansion = meta.get("goal_expansion") or {}
    if isinstance(goal_expansion, dict):
        root_goal = goal_expansion.get("root_goal") or {}
        if isinstance(root_goal, dict):
            root_goal_cfg = root_goal

    target_param = str(root_goal_cfg.get("target_parameter") or "").strip()
    if not target_param:
        issues.append("goal_expansion.root_goal.target_parameter is required")

    for item in meta.get("edges") or []:
        if not isinstance(item, dict):
            continue
        edge_type = str(item.get("type") or "")
        if edge_type in _FORBIDDEN_WORKFLOW_ANCHOR_EDGES:
            issues.append(
                f"workflow edges must not use {edge_type}; "
                "use entry_points with role definition_anchor instead"
            )

    anchor_entry = _definition_anchor_entry(meta)
    if anchor_entry is None:
        issues.append(
            "entry_points must include one definition_anchor (parameter matching target_parameter)"
        )
    else:
        entry_param = str(anchor_entry.get("parameter") or "").strip()
        if not entry_param:
            issues.append(
                "definition_anchor entry_points must use parameter (not paragraph) "
                "matching goal_expansion.root_goal.target_parameter"
            )
        elif target_param and entry_param != target_param:
            issues.append(
                f"definition_anchor parameter {entry_param!r} must match "
                f"goal_expansion.root_goal.target_parameter {target_param!r}"
            )

    completion = root_goal_cfg.get("completion")
    if not isinstance(completion, dict):
        issues.append("goal_expansion.root_goal.completion is required")
    else:
        when = str(completion.get("when") or "").strip()
        status = str(completion.get("status") or "").strip()
        if when != _EXPECTED_COMPLETION_WHEN:
            issues.append(
                f"goal_expansion.root_goal.completion.when must be {_EXPECTED_COMPLETION_WHEN!r}"
            )
        if status != _EXPECTED_COMPLETION_STATUS:
            issues.append(
                f"goal_expansion.root_goal.completion.status must be {_EXPECTED_COMPLETION_STATUS!r}"
            )

    return issues


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
    issues.extend(validate_workflow_goal_anchor(meta))
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="workflow", allow_legacy=False)
            )
    return issues
