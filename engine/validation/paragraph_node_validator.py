"""Validate paragraph knowledge nodes against the template."""

from __future__ import annotations

import re
from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.validation.node_revision_metadata import validate_revision_metadata
from engine.validation.structural_edges import validate_no_structural_edges

_SUBSECTION_ID_RE = re.compile(r"^(.+)-([a-z])$")

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
        "paragraph_class",
        "applicability",
        "limitations",
        "exceptions",
        "calculation_logic",
        "validation_logic",
        "introduced_parameters",
        "referenced_equations",
        "referenced_concepts",
        "referenced_validation_rules",
        "engineering_intent",
    }
)

_KNOWN_AUTHORITIES = frozenset({"AUTH-ASME-B31.3", "AUTH-ASME-B36.10M", "AUTH-ASTM-A106"})

_NOMENCLATURE_FORBIDDEN_EDGE_TYPES = frozenset(
    {
        "references_table",
        "references_concept",
        "references_equation",
        "references_lookup",
        "references_validation_rule",
        "related_to",
    }
)

_ALLOWED_NOMENCLATURE_EDGE_TYPES = frozenset({"belongs_to_authority", "introduces_parameter"})


def _is_nomenclature_paragraph(meta: dict[str, Any], metadata: dict[str, Any]) -> bool:
    if str(metadata.get("kind") or "").strip() == "nomenclature":
        return True
    edge_types: set[str] = set()
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            edge_types.add(str(item.get("type") or "").strip())
    non_authority = edge_types - {"belongs_to_authority"}
    return bool(non_authority) and non_authority <= {"introduces_parameter"}


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
    node_id = str(meta.get("id") or "")
    paragraph_number = str(meta.get("paragraph_number") or "")
    if node_id and paragraph_number and node_id != paragraph_number:
        issues.append("paragraph_number must match id")
    subsection_match = _SUBSECTION_ID_RE.match(node_id)
    if subsection_match and "(" in paragraph_number:
        issues.append("subsection paragraph_number must use hyphen form, not parentheses")
    text = meta.get("text") or {}
    if not isinstance(text, dict) or not str(text.get("original") or "").strip():
        issues.append("text.original required")
    if isinstance(text, dict) and text.get("source_language"):
        issues.append("text.source_language is inherited from pack.yaml; do not set on paragraph nodes")
    hierarchy = meta.get("hierarchy")
    if not isinstance(hierarchy, dict):
        issues.append("missing hierarchy block")
    elif "parent" not in hierarchy:
        issues.append("hierarchy.parent required")
    elif "children" not in hierarchy:
        issues.append("hierarchy.children required (use [] for leaf paragraphs)")
    elif "previous" in hierarchy or "next" in hierarchy:
        issues.append(
            "hierarchy.previous/next are not allowed; use parent children order and workflow edges"
        )
    issues.extend(validate_no_links_metadata(meta))
    metadata = meta.get("metadata") or {}
    if not isinstance(metadata, dict) or not metadata.get("source_revision_year"):
        issues.append("metadata.source_revision_year required")
    issues.extend(validate_revision_metadata(meta))
    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field: {field}")
    issues.extend(validate_no_structural_edges(meta, node_type="paragraph"))
    is_nomenclature = _is_nomenclature_paragraph(meta, metadata if isinstance(metadata, dict) else {})
    for item in meta.get("edges") or []:
        if not isinstance(item, dict):
            continue
        edge_type = str(item.get("type") or "").strip()
        if is_nomenclature and edge_type in _NOMENCLATURE_FORBIDDEN_EDGE_TYPES:
            issues.append(
                f"nomenclature paragraphs must not use edge type: {edge_type}; "
                "use introduces_parameter on the paragraph and used_by on PARAM-* nodes"
            )
            continue
        if is_nomenclature and edge_type not in _ALLOWED_NOMENCLATURE_EDGE_TYPES:
            issues.append(
                f"nomenclature paragraphs may only use edges: "
                f"{', '.join(sorted(_ALLOWED_NOMENCLATURE_EDGE_TYPES))}"
            )
            continue
        issues.extend(
            validate_edge_item(item, source_node_type="paragraph", allow_legacy=False)
        )
    return issues
