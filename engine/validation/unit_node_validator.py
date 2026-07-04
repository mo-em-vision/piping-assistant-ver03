"""Validate unit knowledge nodes and converts_to edge rules."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.validation.node_revision_metadata import validate_revision_metadata


def _validate_converts_to_edge(
    edge: dict[str, Any],
    *,
    from_unit_id: str,
    known_nodes: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    issues: list[str] = []
    target = str(edge.get("target") or "").strip()
    if not target.startswith("UNIT-"):
        issues.append(f"converts_to target must be UNIT-*: {target!r}")

    has_factor = "factor" in edge
    has_equation = bool(str(edge.get("equation") or "").strip())
    if has_factor and has_equation:
        issues.append("converts_to must not specify both factor and equation")
    if not has_factor and not has_equation:
        issues.append("converts_to requires factor or equation metadata")
        return issues

    if has_factor:
        offset = float(edge.get("offset", 0) or 0)
        if offset != 0:
            issues.append(
                "converts_to with non-zero offset must use equation instead of factor"
            )

    if has_equation:
        equation_id = str(edge.get("equation") or "").strip()
        if known_nodes is not None:
            equation_meta = known_nodes.get(equation_id)
            if equation_meta is None:
                issues.append(f"unknown equation referenced by converts_to: {equation_id}")
            elif str(equation_meta.get("type") or "") != "equation":
                issues.append(f"converts_to equation target is not type equation: {equation_id}")
            else:
                conversion = equation_meta.get("conversion") or {}
                if str(conversion.get("from_unit") or "") != from_unit_id:
                    issues.append(
                        f"equation {equation_id} from_unit does not match edge source {from_unit_id}"
                    )
                if str(conversion.get("to_unit") or "") != target:
                    issues.append(
                        f"equation {equation_id} to_unit does not match edge target {target}"
                    )
    return issues


def validate_unit_node(
    meta: dict[str, Any],
    *,
    known_nodes: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    """Return validation issues for one unit node."""
    issues: list[str] = []
    if meta.get("type") != "unit":
        issues.append("type must be 'unit'")
        return issues

    node_id = str(meta.get("id") or "")
    if not node_id.startswith("UNIT-"):
        issues.append("id must start with 'UNIT-'")
    if not str(meta.get("symbol") or "").strip():
        issues.append("missing symbol")
    if not str(meta.get("dimension") or "").startswith("DIM-"):
        issues.append("dimension must reference a DIM-* node")

    issues.extend(validate_revision_metadata(meta))
    issues.extend(validate_no_links_metadata(meta))

    converts_edges = [
        item
        for item in (meta.get("edges") or [])
        if isinstance(item, dict) and str(item.get("type") or "") == "converts_to"
    ]
    conversion = meta.get("conversion") or {}
    is_canonical = (
        isinstance(conversion, dict)
        and str(conversion.get("target") or "") == node_id
        and float(conversion.get("factor", 1) or 1) == 1.0
        and float(conversion.get("offset", 0) or 0) == 0.0
    )
    if not is_canonical and not converts_edges:
        issues.append("non-canonical unit must declare at least one converts_to edge")

    for edge in converts_edges:
        issues.extend(
            _validate_converts_to_edge(
                edge,
                from_unit_id=node_id,
                known_nodes=known_nodes,
            )
        )

    for item in meta.get("edges") or []:
        if isinstance(item, dict) and str(item.get("type") or "") != "converts_to":
            issues.extend(
                validate_edge_item(item, source_node_type="unit", allow_legacy=False)
            )
    return issues


def validate_unit_pack(nodes: dict[str, dict[str, Any]]) -> list[str]:
    """Validate all unit and unit-transformation equation nodes in a pack."""
    issues: list[str] = []
    for node_id, meta in nodes.items():
        node_type = str(meta.get("type") or "")
        if node_type == "unit":
            issues.extend(validate_unit_node(meta, known_nodes=nodes))
        elif node_type == "equation" and node_id.startswith("EQ-unit-"):
            from engine.validation.equation_node_validator import validate_equation_node

            issues.extend(validate_equation_node(meta))
    return issues
