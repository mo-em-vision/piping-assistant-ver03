"""Validate validation_rule knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.equation_authoring_policy import validator_fail_messages_for_equation
from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.validation.authority_authorization import validate_authority_authorization
from engine.validation.node_revision_metadata import validate_revision_metadata
from engine.validation.structural_edges import validate_no_structural_edges

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
    }
)


def validate_validation_rule_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "validation_rule":
        issues.append("type must be 'validation_rule'")
    if not meta.get("key"):
        issues.append("missing key")
    if not meta.get("name"):
        issues.append("missing name")
    if not meta.get("description"):
        issues.append("missing description")

    rule_class = str(meta.get("rule_class") or "")
    if rule_class and rule_class != "validation":
        issues.append(f"rule_class must be 'validation', got {rule_class!r}")

    validates = meta.get("validates")
    has_validates_edge = _has_edge(meta, "validates_parameter")
    if validates is None and not has_validates_edge:
        issues.append("validates list or validates_parameter edge required")

    issues.extend(validate_authority_authorization(meta, node_type="validation_rule"))

    metadata = meta.get("metadata") or {}
    if metadata and not isinstance(metadata, dict):
        issues.append("metadata must be a dict")
    elif isinstance(metadata, dict) and metadata and not metadata.get("status"):
        issues.append("metadata.status required")
    issues.extend(validate_revision_metadata(meta))
    issues.extend(validator_fail_messages_for_equation(meta))

    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")

    issues.extend(validate_no_links_metadata(meta))
    issues.extend(validate_no_structural_edges(meta, node_type="validation_rule"))

    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            edge_type = str(item.get("type") or "")
            if edge_type == "authorized_by":
                continue
            if edge_type == "calculates_parameter":
                issues.append(
                    "validation_rule must use validates_parameter, not calculates_parameter"
                )
            issues.extend(
                validate_edge_item(
                    item, source_node_type="validation_rule", allow_legacy=False
                )
            )
    return issues


def _has_edge(meta: dict[str, Any], edge_type: str) -> bool:
    for item in meta.get("edges") or []:
        if isinstance(item, dict) and str(item.get("type") or "") == edge_type:
            return True
    return False
