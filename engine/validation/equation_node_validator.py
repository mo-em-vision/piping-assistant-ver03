"""Validate equation knowledge nodes against the template."""

from __future__ import annotations

from typing import Any

from engine.reference.equation_authoring_policy import validator_fail_messages_for_equation
from engine.reference.equation_metadata import equation_reference
from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.validation.authority_authorization import validate_authority_authorization
from engine.validation.binding_block_consistency import validate_binding_block_consistency
from engine.validation.node_revision_metadata import validate_revision_metadata
from engine.validation.structural_edges import validate_no_structural_edges

ALLOWED_EQUATION_CLASSES = frozenset(
    {
        "calculation",
        "aggregation",
        "transformation",
    }
)

ALLOWED_CALCULATION_KINDS = frozenset(
    {
        "algebraic",
        "piecewise",
        "conditional",
        "iterative",
        "function",
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


def _validate_unit_symbol_binding(items: Any, *, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(items, list) or not items:
        issues.append(f"{label} must be a non-empty list")
        return issues
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            issues.append(f"{label}[{index}] must be a dict")
            continue
        if not str(item.get("symbol") or "").strip():
            issues.append(f"{label}[{index}] missing symbol")
        if not str(item.get("unit") or "").strip().startswith("UNIT-"):
            issues.append(f"{label}[{index}] missing or invalid unit")
    return issues


def _validate_unit_transformation_equation(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    node_id = str(meta.get("id") or "")
    if not node_id.startswith("EQ-unit-"):
        issues.append("id must start with 'EQ-unit-' for unit transformation equations")
    if not meta.get("key"):
        issues.append("missing key")
    if not meta.get("name"):
        issues.append("missing name")
    equation_class = str(meta.get("equation_class") or "")
    if equation_class != "transformation":
        issues.append("equation_class must be 'transformation' for EQ-unit-* equations")
    calc_kind = str(meta.get("calculation_kind") or "")
    if calc_kind and calc_kind not in ALLOWED_CALCULATION_KINDS:
        issues.append(f"unknown calculation_kind: {calc_kind}")
    if not meta.get("description"):
        issues.append("missing description")
    conversion = meta.get("conversion") or {}
    if not isinstance(conversion, dict):
        issues.append("conversion block required")
    else:
        if not str(conversion.get("from_unit") or "").startswith("UNIT-"):
            issues.append("conversion.from_unit must be a UNIT-* id")
        if not str(conversion.get("to_unit") or "").startswith("UNIT-"):
            issues.append("conversion.to_unit must be a UNIT-* id")
    expression = meta.get("expression") or {}
    if not isinstance(expression, dict) or not str(expression.get("formula") or "").strip():
        issues.append("expression.formula required")
    issues.extend(_validate_unit_symbol_binding(meta.get("requires"), label="requires"))
    issues.extend(_validate_unit_symbol_binding(meta.get("calculates"), label="calculates"))
    metadata = meta.get("metadata") or {}
    if not isinstance(metadata, dict):
        issues.append("metadata must be a dict")
    elif not metadata.get("status"):
        issues.append("metadata.status required")
    issues.extend(validate_revision_metadata(meta))
    issues.extend(validator_fail_messages_for_equation(meta))
    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")
    issues.extend(validate_no_links_metadata(meta))
    issues.extend(validate_no_structural_edges(meta, node_type="equation"))
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            if str(item.get("type") or "") == "authorized_by":
                continue
            issues.extend(
                validate_edge_item(item, source_node_type="equation", allow_legacy=False)
            )
    issues.extend(validate_binding_block_consistency(meta))
    return issues


def _validate_standards_equation(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    node_id = str(meta.get("id") or "")
    if not node_id.startswith("asme-b313-"):
        issues.append("id must start with 'asme-b313-' for standards-pack equations")
    if not meta.get("key"):
        issues.append("missing key")
    if not meta.get("name"):
        issues.append("missing name")
    equation_class = str(meta.get("equation_class") or "")
    if not equation_class:
        issues.append("missing equation_class")
    elif equation_class not in ALLOWED_EQUATION_CLASSES:
        issues.append(f"unknown equation_class: {equation_class}")
    elif equation_class in {"lookup", "validation"}:
        issues.append(
            f"equation_class {equation_class!r} not allowed; use lookup or validation_rule node type"
        )
    calc_kind = str(meta.get("calculation_kind") or "")
    if calc_kind and calc_kind not in ALLOWED_CALCULATION_KINDS:
        issues.append(f"unknown calculation_kind: {calc_kind}")
    if not meta.get("description"):
        issues.append("missing description")
    if "-eq-" in node_id and not equation_reference(meta):
        issues.append("missing equation_number")
    calc_kind = str(meta.get("calculation_kind") or "")
    has_execution = bool(
        meta.get("executor") or str((meta.get("expression") or {}).get("formula") or "").strip()
    )
    if calc_kind == "function" and not has_execution:
        issues.append("missing executor or expression.formula")
    issues.extend(validate_authority_authorization(meta, node_type="equation"))
    requires = meta.get("requires")
    calculates = meta.get("calculates")
    if requires is None and calculates is None:
        issues.append("requires or calculates required")
    metadata = meta.get("metadata") or {}
    if not isinstance(metadata, dict):
        issues.append("metadata must be a dict")
    elif not metadata.get("status"):
        issues.append("metadata.status required")
    issues.extend(validate_revision_metadata(meta))
    issues.extend(validator_fail_messages_for_equation(meta))
    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")
    issues.extend(validate_no_links_metadata(meta))
    issues.extend(validate_no_structural_edges(meta, node_type="equation"))
    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            if str(item.get("type") or "") == "authorized_by":
                continue
            issues.extend(
                validate_edge_item(item, source_node_type="equation", allow_legacy=False)
            )
    issues.extend(validate_binding_block_consistency(meta))
    return issues


def validate_equation_node(meta: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "equation":
        issues.append("type must be 'equation'")
        return issues
    node_id = str(meta.get("id") or "")
    if node_id.startswith("EQ-unit-"):
        return _validate_unit_transformation_equation(meta)
    if node_id.startswith("asme-b313-"):
        return _validate_standards_equation(meta)
    issues.append("id must start with 'asme-b313-' or 'EQ-unit-'")
    return issues
