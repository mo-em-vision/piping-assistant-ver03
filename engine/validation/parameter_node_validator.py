"""Validate parameter knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.reference.asme_b313_node_ids import (
    is_qualified_paragraph_ref,
    qualify_cross_pack_ref,
)
from engine.reference.parameter_keys import validate_parameter_identity_fields
from engine.validation.node_revision_metadata import validate_revision_metadata

ALLOWED_PARAMETER_CLASSES = frozenset(
    {
        "physical_quantity",
        "geometric_quantity",
        "material_designation",
        "coefficient",
        "factor",
        "categorical",
        "environmental_condition",
        "calculated_quantity",
        "selection",
    }
)

_FORBIDDEN_FIELDS = frozenset(
    {
        "value",
        "unit",
        "resolution",
        "source",
        "timestamp",
        "execution_id",
        "workflow_id",
        "status",
    }
)


def validate_parameter_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "parameter":
        issues.append("type must be 'parameter'")
    node_id = str(meta.get("id") or "")
    if not node_id.startswith("PARAM-"):
        issues.append("id must start with PARAM-")
    if not meta.get("key"):
        issues.append("missing key")
    if not meta.get("name"):
        issues.append("missing name")
    parameter_class = str(meta.get("parameter_class") or "")
    if not parameter_class:
        issues.append("missing parameter_class")
    elif parameter_class not in ALLOWED_PARAMETER_CLASSES:
        issues.append(f"unknown parameter_class: {parameter_class}")
    if not meta.get("description"):
        issues.append("missing description")
    issues.extend(validate_parameter_identity_fields(meta))
    issues.extend(validate_revision_metadata(meta))
    issues.extend(validate_no_links_metadata(meta))
    for ref in meta.get("introduced_by") or []:
        text = str(ref).strip()
        if text and text[0].isdigit() and not is_qualified_paragraph_ref(text):
            issues.append(
                f"introduced_by paragraph reference must use pack-qualified id, not bare: {text}"
            )
        if text.startswith("asme_b313_") or text.startswith("B313-"):
            issues.append(
                f"introduced_by must use {qualify_cross_pack_ref(text)} (asme-b313- prefix), not legacy: {text}"
            )
    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field: {field}")
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            edge_type = str(item.get("type") or "").strip()
            if edge_type == "introduced_by":
                issues.append(
                    "introduced_by must be in top-level introduced_by list, not edges"
                )
                continue
            target = str(item.get("target") or "").strip()
            if target and (target.startswith("asme_b313_") or target.startswith("B313-")):
                issues.append(
                    f"edge target must use asme-b313- qualified id, not legacy: {target}"
                )
            issues.extend(
                validate_edge_item(item, source_node_type="parameter", allow_legacy=False)
            )
    return issues
