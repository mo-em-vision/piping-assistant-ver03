"""Validate dimension knowledge nodes against audits/contracts/nodes/dimension.md."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.reference.graph_edge_schema import dimension_allowed_unit_ids
from engine.validation.node_revision_metadata import validate_revision_metadata

_ALLOWED_KINDS = frozenset({"physical", "dimensionless", "categorical"})

_FORBIDDEN_FIELDS = frozenset(
    {
        "runtime_value",
        "fact_value",
        "user_input",
        "value",
        "factor",
        "offset",
    }
)


def validate_dimension_node(
    meta: dict[str, Any],
    *,
    known_unit_ids: set[str] | None = None,
) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "dimension":
        issues.append("type must be 'dimension'")
    node_id = str(meta.get("id") or "").strip()
    if not node_id.startswith("DIM-"):
        issues.append("id must start with DIM-")
    for key in ("key", "name", "dimension_kind", "description"):
        if not meta.get(key):
            issues.append(f"missing {key}")

    kind = str(meta.get("dimension_kind") or "").strip()
    if kind and kind not in _ALLOWED_KINDS:
        issues.append(f"invalid dimension_kind: {kind!r}")

    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")

    allowed = dimension_allowed_unit_ids(meta)
    canonical = meta.get("canonical_unit")
    canonical_s = str(canonical or "").strip()

    if kind == "categorical":
        if canonical not in (None, "null", "") and canonical_s:
            issues.append("categorical dimension must not set canonical_unit")
        if allowed:
            issues.append("categorical dimension must not declare allows_unit edges")
    elif kind in {"physical", "dimensionless"}:
        if not canonical_s:
            issues.append(f"{kind} dimension missing canonical_unit")
        elif known_unit_ids is not None and canonical_s not in known_unit_ids:
            issues.append(f"canonical_unit {canonical_s!r} not found in UNIT-* nodes")
        if not allowed:
            issues.append(f"{kind} dimension missing allows_unit edges")
        elif canonical_s and canonical_s not in allowed:
            issues.append("canonical_unit must appear in allows_unit edges")
        if known_unit_ids is not None:
            for unit_id in allowed:
                if unit_id not in known_unit_ids:
                    issues.append(f"allows_unit target {unit_id!r} not found in UNIT-* nodes")

    for item in meta.get("edges") or []:
        if isinstance(item, dict) and str(item.get("type") or "") == "references":
            issues.append("use allows_unit instead of references for unit membership")

    issues.extend(validate_revision_metadata(meta))
    issues.extend(validate_no_links_metadata(meta))

    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="dimension", allow_legacy=False)
            )
    return issues
