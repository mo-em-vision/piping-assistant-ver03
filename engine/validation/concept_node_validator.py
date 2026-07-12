"""Validate concept knowledge nodes against audits/contracts/nodes/concept.md."""

from __future__ import annotations

from typing import Any

from engine.reference.graph_compile import validate_edge_item, validate_no_links_metadata
from engine.reference.graph_edge_schema import edge_targets
from engine.validation.node_revision_metadata import validate_revision_metadata

VALID_CONCEPT_CLASSES = frozenset(
    {
        "physical_quantity",
        "geometric_quantity",
        "material",
        "fluid",
        "component",
        "condition",
        "coefficient",
        "factor",
        "selection",
        "failure_mode",
        "inspection_method",
        "authority_concept",
    }
)

FORBIDDEN_CONCEPT_CLASSES = frozenset({"category", "categorical"})

_PHYSICAL_CONCEPT_CLASSES = frozenset({"physical_quantity", "geometric_quantity"})

_FORBIDDEN_FIELDS = frozenset(
    {
        "value",
        "unit",
        "source",
        "timestamp",
        "execution_id",
        "workflow_id",
        "project_id",
        "resolution",
        "formula",
        "calculation_result",
    }
)


def validate_concept_node(
    meta: dict[str, Any],
    *,
    known_dimension_ids: set[str] | None = None,
) -> list[str]:
    issues: list[str] = []
    if meta.get("type") != "concept":
        issues.append("type must be 'concept'")
    node_id = str(meta.get("id") or "").strip()
    if not node_id.startswith("CONCEPT-"):
        issues.append("id must start with CONCEPT-")
    for key in ("key", "name", "description"):
        if not meta.get(key):
            issues.append(f"missing {key}")

    concept_class = str(meta.get("concept_class") or "").strip()
    if not concept_class:
        issues.append("missing concept_class")
    elif concept_class in FORBIDDEN_CONCEPT_CLASSES:
        issues.append(f"forbidden concept_class: {concept_class}")
    elif concept_class not in VALID_CONCEPT_CLASSES:
        issues.append(f"unknown concept_class: {concept_class}")

    for field in _FORBIDDEN_FIELDS:
        if field in meta:
            issues.append(f"forbidden field in frontmatter: {field}")

    dimension = meta.get("dimension")
    dimension_s = str(dimension or "").strip()
    has_dimension = edge_targets(meta, "has_dimension")

    if concept_class in _PHYSICAL_CONCEPT_CLASSES:
        if not dimension_s or not dimension_s.startswith("DIM-"):
            issues.append(f"{concept_class} concept requires dimension: DIM-*")
        elif known_dimension_ids is not None and dimension_s not in known_dimension_ids:
            issues.append(f"dimension {dimension_s!r} not found in DIM-* nodes")
        if has_dimension != ([dimension_s] if dimension_s else []):
            issues.append("has_dimension edges must match dimension field exactly")
    elif concept_class and concept_class not in _PHYSICAL_CONCEPT_CLASSES:
        if dimension not in (None, "null") and dimension_s:
            issues.append(f"{concept_class} concept must not declare dimension")
        if has_dimension:
            issues.append(f"{concept_class} concept must not declare has_dimension edges")

    issues.extend(validate_revision_metadata(meta))
    issues.extend(validate_no_links_metadata(meta))

    for item in meta.get("edges") or []:
        if isinstance(item, dict):
            issues.extend(
                validate_edge_item(item, source_node_type="concept", allow_legacy=False)
            )
    return issues
