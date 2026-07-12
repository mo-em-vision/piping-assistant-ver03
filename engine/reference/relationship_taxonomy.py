"""Relationship taxonomy — controlled vocabulary for knowledge-graph edges."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def edge_target(item: dict[str, Any]) -> str:
    return str(item.get("target") or item.get("to") or item.get("node_id") or item.get("id") or "").strip()

# --- Ontology ---
_ONTOLOGY = frozenset(
    {
        "has_concept",
        "has_dimension",
        "allows_unit",
        "belongs_to_dimension",
        "converts_to",
        "property_of",
        "specializes",
        "generalizes",
        "related_to",
        "has_parameter",
        "parameter_of",
    }
)

# --- Authority ---
_AUTHORITY = frozenset(
    {
        "belongs_to_authority",
        "contains_paragraph",
        "contains_table",
        "contains_rule",
        "references_authority",
        "refines_authority",
        "conflicts_with_authority",
    }
)

# --- Paragraph / equation / lookup / validation_rule / workflow (knowledge) ---
_PARAGRAPH_EQ_WF = frozenset(
    {
        "introduces_parameter",
        "references_concept",
        "references_equation",
        "references_lookup",
        "references_validation_rule",
        "references_table",
        "note_for_table",
        "has_table_note",
        "constrains_parameter",
        "redirects_to",
        "authorized_by",
        "requires_parameter",
        "calculates_parameter",
        "returns_parameter",
        "reads_table",
        "validates_parameter",
        "constrains_equation",
        "creates_warning",
        "depends_on_equation",
        "uses_authority",
        "may_use_authority",
        "starts_from_paragraph",
        "may_use_equation",
        "may_use_lookup",
        "may_use_validation_rule",
        "may_create_goal",
    }
)

# --- Structural / execution routing (knowledge graph) ---
_STRUCTURAL = frozenset(
    {
        "parent",
        "child",
        "next",
        "previous",
        "depends_on",
        "dependency_of",
        "implements",
        "implemented_by",
    }
)

# --- Provenance traceability on ontology nodes ---
_TRACEABILITY = frozenset(
    {
        "introduced_by",
        "introduces",
        "used_by",
        "consumed_by",
    }
)

# --- Lifecycle (knowledge nodes) ---
_LIFECYCLE = frozenset(
    {
        "supersedes",
        "superseded_by",
        "deprecated_by",
        "equivalent_to",
        "alias_of",
    }
)

KNOWLEDGE_EDGE_TYPES = frozenset(
    _ONTOLOGY | _AUTHORITY | _PARAGRAPH_EQ_WF | _STRUCTURAL | _TRACEABILITY | _LIFECYCLE
)

# Runtime-only types (documented; not stored on immutable knowledge YAML).
RUNTIME_ONLY_EDGE_TYPES = frozenset(
    {
        "instantiates",
        "derived_from",
        "supersedes_fact",
        "conflicts_with_fact",
        "satisfies_goal",
        "activates_authority",
        "activates_paragraph",
        "activates_table",
        "requires_fact",
        "satisfied_by",
        "expands_to",
        "blocked_by",
        "belongs_to_execution_context",
        "governs_execution_context",
        "produced_by",
        "recorded_event",
        "validated_by",
        "requires_validation",
        "failed_because",
        "records_override",
        "included_in_report",
        "explains",
        "supports_conclusion",
        "produces_validation_result",
        "blocks_goal",
    }
)

TAXONOMY_EDGE_TYPES = KNOWLEDGE_EDGE_TYPES | RUNTIME_ONLY_EDGE_TYPES

# Legacy transport types accepted only at import/migration boundaries.
LEGACY_TRANSPORT_TYPES = frozenset(
    {
        "references",
        "referenced_by",
        "requires",
        "required_by",
        "parameter",
        "equation",
        "material",
        "table",
        "figure",
        "note",
        "dataset",
        "contains",
        "contained_by",
        "uses",
        "constrains",
        "constrained_by",
    }
)

DISCOURAGED_GENERIC_TYPES = frozenset({"references", "links_to", "related", "uses", "contains"})

# references + role → taxonomy
REFERENCE_ROLE_TO_TAXONOMY: dict[str, str] = {
    "belongs_to_authority": "belongs_to_authority",
    "authorized_by": "authorized_by",
    "starts_from_paragraph": "starts_from_paragraph",
    "uses_authority": "uses_authority",
    "may_use_authority": "may_use_authority",
    "refines": "refines_authority",
    "refines_authority": "refines_authority",
    "references_authority": "references_authority",
    "references_equation": "references_equation",
    "references_lookup": "references_lookup",
    "references_validation_rule": "references_validation_rule",
    "references_table": "references_table",
    "references_concept": "references_concept",
    "introduces_parameter": "introduces_parameter",
    "constrains_parameter": "constrains_parameter",
    "defines_material_specification": "constrains_parameter",
    "calculates": "calculates_parameter",
    "calculates_parameter": "calculates_parameter",
    "paragraph": "contains_paragraph",
}

# Query expansion: taxonomy type → additional legacy types still in graph DB during transition
TAXONOMY_TO_LEGACY_QUERY_ALIASES: dict[str, frozenset[str]] = {
    "belongs_to_authority": frozenset({"references"}),
    "authorized_by": frozenset({"references"}),
    "starts_from_paragraph": frozenset({"references"}),
    "uses_authority": frozenset({"references"}),
    "references_equation": frozenset({"equation"}),
    "references_table": frozenset({"table", "references"}),
    "introduces_parameter": frozenset({"parameter", "implements"}),
    "requires_parameter": frozenset({"requires"}),
    "calculates_parameter": frozenset({"parameter"}),
    "contains_paragraph": frozenset({"contains"}),
    "contains_table": frozenset({"table", "contains"}),
    "constrains_parameter": frozenset({"constrains"}),
    "may_use_equation": frozenset({"equation"}),
    "may_use_lookup": frozenset({"lookup"}),
    "references_lookup": frozenset({"requires_lookup"}),
    "reads_table": frozenset({"table", "used_by_lookup"}),
    "returns_parameter": frozenset({"parameter"}),
    "depends_on_equation": frozenset({"depends_on", "equation"}),
    "redirects_to": frozenset({"next"}),
    "related_to": frozenset({"references"}),
}

LEGACY_TO_TAXONOMY_QUERY_ALIASES: dict[str, frozenset[str]] = {}
for _tax, _legacy_set in TAXONOMY_TO_LEGACY_QUERY_ALIASES.items():
    for _leg in _legacy_set:
        prior = LEGACY_TO_TAXONOMY_QUERY_ALIASES.get(_leg, frozenset())
        LEGACY_TO_TAXONOMY_QUERY_ALIASES[_leg] = prior | {_tax}

# Common query bundles (expanded via expand_edge_types_for_query at use site).
DEPENDENCY_TRAVERSAL_TYPES = frozenset(
    {
        "depends_on",
        "depends_on_equation",
        "related_to",
        "references",
        "references_table",
        "references_equation",
        "references_lookup",
        "reads_table",
        "belongs_to_authority",
        "references_authority",
        "table",
        "uses",
        "may_use_authority",
        "starts_from_paragraph",
    }
)

REQUIRES_TRAVERSAL_TYPES = frozenset({"requires", "requires_parameter"})

PARAMETER_CONCEPT_TRAVERSAL_TYPES = frozenset(
    {"references", "has_parameter", "has_concept", "introduces_parameter"}
)

CONTAINS_TRAVERSAL_TYPES = frozenset({"contains", "contains_paragraph", "contains_table"})


@dataclass(frozen=True)
class RelationshipRule:
    source_types: frozenset[str] | None = None
    target_prefixes: frozenset[str] | None = None


RELATIONSHIP_RULES: dict[str, RelationshipRule] = {
    "has_concept": RelationshipRule(source_types=frozenset({"parameter"}), target_prefixes=frozenset({"CONCEPT-"})),
    "has_dimension": RelationshipRule(
        source_types=frozenset({"parameter", "concept"}),
        target_prefixes=frozenset({"DIM-"}),
    ),
    "allows_unit": RelationshipRule(source_types=frozenset({"dimension"}), target_prefixes=frozenset({"UNIT-"})),
    "belongs_to_dimension": RelationshipRule(source_types=frozenset({"unit"}), target_prefixes=frozenset({"DIM-"})),
    "belongs_to_authority": RelationshipRule(
        source_types=frozenset({"paragraph", "table", "standard_section"}),
        target_prefixes=frozenset({"AUTH-"}),
    ),
    "contains_paragraph": RelationshipRule(source_types=frozenset({"authority"})),
    "contains_table": RelationshipRule(source_types=frozenset({"authority"}), target_prefixes=frozenset({"B313-table", "TABLE-"})),
    "authorized_by": RelationshipRule(
        source_types=frozenset({"equation", "lookup", "validation_rule"}),
    ),
    "requires_parameter": RelationshipRule(
        source_types=frozenset({"equation", "lookup", "validation_rule", "workflow", "paragraph", "calculation"}),
        target_prefixes=frozenset({"PARAM-", "param-"}),
    ),
    "calculates_parameter": RelationshipRule(
        source_types=frozenset({"equation", "calculation"}),
        target_prefixes=frozenset({"PARAM-", "param-"}),
    ),
    "returns_parameter": RelationshipRule(
        source_types=frozenset({"lookup"}),
        target_prefixes=frozenset({"PARAM-", "param-"}),
    ),
    "reads_table": RelationshipRule(
        source_types=frozenset({"lookup"}),
        target_prefixes=frozenset({"B313-table", "TABLE-"}),
    ),
    "validates_parameter": RelationshipRule(
        source_types=frozenset({"validation_rule", "rule"}),
        target_prefixes=frozenset({"PARAM-", "param-"}),
    ),
    "constrains_equation": RelationshipRule(
        source_types=frozenset({"validation_rule"}),
    ),
    "creates_warning": RelationshipRule(
        source_types=frozenset({"validation_rule"}),
    ),
    "references_equation": RelationshipRule(source_types=frozenset({"paragraph", "workflow"})),
    "references_lookup": RelationshipRule(source_types=frozenset({"paragraph", "workflow"})),
    "references_validation_rule": RelationshipRule(source_types=frozenset({"paragraph", "workflow"})),
    "references_table": RelationshipRule(source_types=frozenset({"paragraph", "workflow"})),
    "note_for_table": RelationshipRule(source_types=frozenset({"table_note"})),
    "has_table_note": RelationshipRule(source_types=frozenset({"lookup", "table"})),
    "starts_from_paragraph": RelationshipRule(source_types=frozenset({"workflow"})),
    "may_use_equation": RelationshipRule(source_types=frozenset({"workflow"})),
    "may_use_lookup": RelationshipRule(source_types=frozenset({"workflow"})),
    "may_use_validation_rule": RelationshipRule(source_types=frozenset({"workflow"})),
    "introduces_parameter": RelationshipRule(
        source_types=frozenset({"paragraph"}),
        target_prefixes=frozenset({"PARAM-", "param-"}),
    ),
    "constrains_parameter": RelationshipRule(
        source_types=frozenset({"authority", "paragraph", "table"}),
        target_prefixes=frozenset({"PARAM-"}),
    ),
}


def _target_prefix(target: str) -> str:
    if target.startswith("AUTH-"):
        return "AUTH-"
    if target.startswith("CONCEPT-"):
        return "CONCEPT-"
    if target.startswith("DIM-"):
        return "DIM-"
    if target.startswith("UNIT-"):
        return "UNIT-"
    if target.startswith("PARAM-"):
        return "PARAM-"
    if target.startswith("param-"):
        return "param-"
    if target.startswith("B313-table") or target.startswith("TABLE-"):
        return "B313-table"
    return ""


def _infer_reference_taxonomy(item: dict[str, Any], *, source_node_type: str) -> str | None:
    role = str(item.get("role") or "").strip()
    if role:
        mapped = REFERENCE_ROLE_TO_TAXONOMY.get(role)
        if mapped:
            return mapped
        if role.lower() == "calculates":
            return "calculates_parameter"
    target = edge_target(item)
    if target.startswith("AUTH-"):
        return "belongs_to_authority" if source_node_type == "paragraph" else "references_authority"
    if target.startswith("B313-table") or target.startswith("TABLE-"):
        return "references_table" if source_node_type != "authority" else "contains_table"
    if target.startswith("CONCEPT-"):
        return "references_concept"
    if source_node_type == "paragraph" and _looks_like_paragraph_id(target):
        return "related_to"
    return None


def _looks_like_paragraph_id(target: str) -> bool:
    text = target.strip()
    if not text or text.startswith(("AUTH-", "PARAM-", "param-", "CONCEPT-", "WF-", "asme_")):
        return False
    return text[0].isdigit() or text.startswith("B313-")


def normalize_authoring_edge(
    item: dict[str, Any],
    *,
    source_node_type: str = "",
    allow_legacy: bool = True,
) -> dict[str, Any] | None:
    """Convert legacy transport edges to taxonomy; pass taxonomy through unchanged."""
    if not isinstance(item, dict):
        return None
    edge_type = str(item.get("type") or "").strip()
    if not edge_type:
        return None

    normalized = dict(item)
    role = str(item.get("role") or "").strip().lower()

    if edge_type in KNOWLEDGE_EDGE_TYPES or edge_type in _STRUCTURAL:
        return normalized

    if not allow_legacy:
        return None

    if edge_type == "requires_lookup":
        normalized["type"] = "references_lookup"
        return normalized

    if edge_type == "used_by_lookup":
        return None

    if edge_type == "references":
        inferred = _infer_reference_taxonomy(item, source_node_type=source_node_type)
        if inferred is None:
            return None
        normalized["type"] = inferred
        if role and role not in REFERENCE_ROLE_TO_TAXONOMY:
            pass
        elif "role" in normalized and normalized["type"] != "references":
            normalized.pop("role", None)
        return normalized

    if edge_type == "requires":
        normalized["type"] = "requires_parameter"
        return normalized

    if edge_type == "parameter":
        if role == "calculates" or role == "calculates_parameter":
            normalized["type"] = "calculates_parameter"
        else:
            normalized["type"] = "introduces_parameter"
        normalized.pop("role", None)
        return normalized

    if edge_type == "equation":
        if source_node_type == "workflow":
            normalized["type"] = "may_use_equation"
        else:
            normalized["type"] = "references_equation"
        return normalized

    if edge_type == "table":
        if source_node_type == "authority":
            normalized["type"] = "contains_table"
        else:
            normalized["type"] = "references_table"
        return normalized

    if edge_type == "contains":
        if role == "paragraph":
            normalized["type"] = "contains_paragraph"
            normalized.pop("role", None)
        elif role == "table":
            normalized["type"] = "contains_table"
            normalized.pop("role", None)
        elif role == "rule":
            normalized["type"] = "contains_rule"
            normalized.pop("role", None)
        else:
            target = edge_target(item)
            if target.startswith("B313-table") or target.startswith("TABLE-"):
                normalized["type"] = "contains_table"
            else:
                normalized["type"] = "contains_paragraph"
            normalized.pop("role", None)
        return normalized

    if edge_type == "constrains":
        normalized["type"] = "constrains_parameter"
        return normalized

    if edge_type == "uses":
        normalized["type"] = "may_use_authority" if source_node_type == "workflow" else "related_to"
        return normalized

    if edge_type == "used_by":
        return normalized

    if edge_type == "introduced_by":
        return normalized

    if edge_type == "introduces":
        normalized["type"] = "introduces_parameter"
        return normalized

    if edge_type in {"parent", "child", "next", "previous", "depends_on", "implements", "implements"}:
        return normalized

    if edge_type in {"has_dimension", "allows_unit", "belongs_to_dimension", "converts_to", "specializes", "generalizes", "has_parameter", "related_to", "alias_of"}:
        return normalized

    return None


def expand_edge_types_for_query(edge_types: set[str] | None) -> set[str] | None:
    """Expand taxonomy query types with legacy aliases for graph_store lookups."""
    if edge_types is None:
        return None
    expanded: set[str] = set(edge_types)
    for edge_type in edge_types:
        for alias in TAXONOMY_TO_LEGACY_QUERY_ALIASES.get(edge_type, frozenset()):
            expanded.add(alias)
        for alias in LEGACY_TO_TAXONOMY_QUERY_ALIASES.get(edge_type, frozenset()):
            expanded.add(alias)
    return expanded


def is_knowledge_edge_type(edge_type: str) -> bool:
    return edge_type in KNOWLEDGE_EDGE_TYPES or edge_type in _STRUCTURAL


def is_legacy_transport_edge(edge_type: str) -> bool:
    return edge_type in LEGACY_TRANSPORT_TYPES


def validate_taxonomy_edge(
    item: dict[str, Any],
    *,
    source_node_type: str = "",
) -> list[str]:
    """Validate one edge against taxonomy rules (after normalization)."""
    issues: list[str] = []
    edge_type = str(item.get("type") or "").strip()
    target = edge_target(item)
    if not edge_type:
        issues.append("missing type")
        return issues
    if not target:
        issues.append("missing target")
        return issues

    if edge_type in LEGACY_TRANSPORT_TYPES and edge_type in DISCOURAGED_GENERIC_TYPES:
        if edge_type == "references" and not item.get("role"):
            issues.append("generic references without role; use a taxonomy relationship type")
        elif edge_type in DISCOURAGED_GENERIC_TYPES:
            issues.append(f"discouraged generic edge type: {edge_type}")

    if edge_type not in KNOWLEDGE_EDGE_TYPES and edge_type not in _STRUCTURAL and edge_type not in LEGACY_TRANSPORT_TYPES:
        if edge_type in RUNTIME_ONLY_EDGE_TYPES:
            issues.append(f"runtime-only edge type not allowed on knowledge nodes: {edge_type}")
        else:
            issues.append(f"unknown edge type: {edge_type}")

    rule = RELATIONSHIP_RULES.get(edge_type)
    if rule and source_node_type and rule.source_types and source_node_type not in rule.source_types:
        issues.append(f"{edge_type} not allowed from source type {source_node_type!r}")
    if rule and rule.target_prefixes:
        prefix = _target_prefix(target)
        if prefix and prefix not in rule.target_prefixes and not any(
            target.startswith(p.rstrip("-")) for p in rule.target_prefixes if p.endswith("-")
        ):
            if not any(target.startswith(p) for p in rule.target_prefixes):
                pass
    return issues
