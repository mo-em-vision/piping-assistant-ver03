"""Validate paragraph knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item

ALLOWED_PARAGRAPH_CLASSES = frozenset(
    {
        "definition",
        "calculation_requirement",
        "lookup_requirement",
        "applicability_requirement",
        "validation_requirement",
        "limitation",
        "exception",
        "note",
        "table_reference",
        "figure_reference",
        "inspection_requirement",
        "testing_requirement",
        "acceptance_criteria",
        "reporting_requirement",
        "material_requirement",
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
    }
)

_KNOWN_AUTHORITIES = frozenset({"AUTH-ASME-B31.3", "AUTH-ASME-B36.10M", "AUTH-ASTM-A106"})


def validate_paragraph_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "paragraph":
        issues.append("type must be 'paragraph'")
    if not meta.get("key"):
        issues.append("missing key")
    if not meta.get("title"):
        issues.append("missing title")
    authority = str(meta.get("authority") or "")
    if not authority.startswith("AUTH-"):
        issues.append("authority must be AUTH-*")
    elif authority not in _KNOWN_AUTHORITIES:
        issues.append(f"unknown authority: {authority}")
    if not meta.get("edition"):
        issues.append("missing edition")
    if not meta.get("paragraph_number"):
        issues.append("missing paragraph_number")
    paragraph_class = str(meta.get("paragraph_class") or "")
    if not paragraph_class:
        issues.append("missing paragraph_class")
    elif paragraph_class not in ALLOWED_PARAGRAPH_CLASSES:
        issues.append(f"unknown paragraph_class: {paragraph_class}")
    if not meta.get("description"):
        issues.append("missing description")
    metadata = meta.get("metadata") or {}
    if not isinstance(metadata, dict) or not metadata.get("source_revision_year"):
        issues.append("metadata.source_revision_year required")
    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field: {field}")
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="paragraph", allow_legacy=False)
            )
    return issues
