"""Cross-check binding blocks against typed edges on raw authored metadata."""

from __future__ import annotations

from typing import Any

_BLOCK_EDGE_PAIRS: tuple[tuple[str, str], ...] = (
    ("requires", "requires_parameter"),
    ("calculates", "calculates_parameter"),
    ("returns", "returns_parameter"),
    ("validates", "validates_parameter"),
)

_BINDING_NODE_TYPES = frozenset({"equation", "lookup", "validation_rule"})


def _block_param_refs(block: Any) -> set[str]:
    if not isinstance(block, list):
        return set()
    refs: set[str] = set()
    for item in block:
        if not isinstance(item, dict):
            continue
        param_id = str(item.get("parameter") or "").strip()
        if param_id.startswith("PARAM-"):
            refs.add(param_id)
    return refs


def _edge_param_targets(meta: dict[str, Any], edge_type: str) -> set[str]:
    targets: set[str] = set()
    for item in meta.get("edges") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").strip() != edge_type:
            continue
        target = str(item.get("target") or "").strip()
        if target.startswith("PARAM-"):
            targets.add(target)
    return targets


def validate_binding_block_consistency(meta: dict[str, Any]) -> list[str]:
    """Compare authored binding blocks to explicit edges before graph compilation."""
    node_type = str(meta.get("type") or "")
    if node_type not in _BINDING_NODE_TYPES:
        return []

    issues: list[str] = []
    for block_key, edge_type in _BLOCK_EDGE_PAIRS:
        if node_type == "validation_rule" and block_key == "validates":
            continue
        block_refs = _block_param_refs(meta.get(block_key))
        edge_refs = _edge_param_targets(meta, edge_type)
        if not block_refs and not edge_refs:
            continue
        for param_id in sorted(block_refs - edge_refs):
            issues.append(
                f"{block_key} lists {param_id} but no matching {edge_type} edge",
            )
        for param_id in sorted(edge_refs - block_refs):
            issues.append(
                f"{edge_type} edge targets {param_id} but {block_key} block omits it",
            )

    if node_type == "validation_rule":
        result = meta.get("result") or {}
        result_param = str(result.get("parameter") or "").strip()
        outcome_edges = _edge_param_targets(meta, "validates_parameter")
        if result_param:
            if result_param not in outcome_edges:
                issues.append(
                    f"result.parameter {result_param} has no validates_parameter edge",
                )
            for param_id in sorted(outcome_edges - {result_param}):
                issues.append(
                    f"validates_parameter edge targets {param_id} but result.parameter differs",
                )
        elif outcome_edges:
            issues.append(
                "validates_parameter edge present but result.parameter is missing",
            )

    return issues
