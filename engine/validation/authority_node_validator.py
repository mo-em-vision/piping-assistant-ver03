"""Validate authority knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.validation.node_revision_metadata import validate_revision_metadata

ALLOWED_AUTHORITY_CLASSES = frozenset(
    {
        "design_code",
        "inspection_code",
        "material_standard",
        "dimensional_standard",
        "testing_standard",
        "regulation",
        "company_standard",
        "project_specification",
        "client_requirement",
        "reference_standard",
        "recommended_practice",
        "engineering_procedure",
        "manufacturer_document",
    }
)

_FORBIDDEN_FIELDS = frozenset(
    {
        "runtime_value",
        "fact_value",
        "execution_id",
        "task_id",
        "selected_for_execution",
        "active_in_context",
        "calculation_result",
        "user_input",
        "value",
        "unit",
        "source",
        "timestamp",
    }
)


def validate_authority_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    node_id = str(meta.get("id") or "")
    if not node_id.startswith("AUTH-"):
        issues.append("id must start with AUTH-")
    if meta.get("type") != "authority":
        issues.append("type must be 'authority'")
    if not meta.get("key"):
        issues.append("missing key")
    if not meta.get("name"):
        issues.append("missing name")
    if not meta.get("authority_class"):
        issues.append("missing authority_class")
    elif str(meta["authority_class"]) not in ALLOWED_AUTHORITY_CLASSES:
        issues.append(f"unknown authority_class: {meta['authority_class']}")
    if not meta.get("description"):
        issues.append("missing description")
    issues.extend(validate_revision_metadata(meta))
    issues.extend(validate_no_links_metadata(meta))
    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field: {field}")

    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="authority", allow_legacy=False)
            )
    return issues
