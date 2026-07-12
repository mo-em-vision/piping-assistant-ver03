"""Canonical field-placement policy for paragraph node frontmatter and sidecars.

Single source of truth for placement categories, permitted destinations, edge-target
classification, and phase-aware SIDECAR_ONLY enforcement. Consumed by the sidecar
loader, paragraph validator, audit script, and ontology tests.
"""

from __future__ import annotations

from typing import Any, Literal

Severity = Literal["FAIL", "WARN", "INFO"]

# Phase 1: WARN on SIDECAR_ONLY keys in frontmatter. Phase 2: FAIL after promotion criteria met.
SIDECAR_ONLY_ENFORCEMENT: Literal["warn", "fail"] = "warn"

FORBIDDEN_RUNTIME_STATE_KEYS: frozenset[str] = frozenset(
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

FORBIDDEN_PARAGRAPH_FRONTMATTER: frozenset[str] = frozenset(
    {
        "applicability",
        "paragraph_class",
        "limitations",
        "exceptions",
        "calculation_logic",
        "validation_logic",
        "introduced_parameters",
        "referenced_equations",
        "referenced_concepts",
        "referenced_validation_rules",
        "engineering_intent",
        "trace",
        "report",
        "ai_hints",
    }
)

# Execution sidecar keys (loaded by paragraph_sidecar.merge_paragraph_sidecar_metadata).
EXECUTION_SIDECAR_KEYS: tuple[str, ...] = (
    "interactions",
    "assumptions",
    "applicability",
    "provisional_assumptions",
    "parameter_defaults",
    "inputs",
    "depends_on",
    "equations",
    "validation_rules",
    "conditions",
    "kind",
    "outputs",
    "lookups",
    "notes",
    "subsections",
)

NOMENCLATURE_SIDECAR_KEY = "nomenclature"

SIDECAR_ONLY_KEYS: frozenset[str] = frozenset(
    {*EXECUTION_SIDECAR_KEYS, NOMENCLATURE_SIDECAR_KEY}
)

KEY_PERMITTED_DESTINATIONS: dict[str, str] = {
    "runtime_value": "Task execution context / Facts",
    "fact_value": "Task execution context / Facts",
    "user_input": "Task execution context",
    "execution_id": "Task execution context",
    "task_id": "Task execution context",
    "calculation_result": "Execution trace / report layer",
    "selected_for_execution": "Planner / expansion runtime",
    "active_in_context": "Execution context",
    "applicability": "{id}.execution.yaml (applicability block)",
    "paragraph_class": "metadata.kind or typed edges",
    "limitations": "{id}.execution.yaml or text.original",
    "exceptions": "{id}.execution.yaml or text.original",
    "calculation_logic": "equation / validation_rule nodes + edges",
    "validation_logic": "validation_rule nodes + edges",
    "introduced_parameters": "introduces_parameter edges + PARAM-* nodes",
    "referenced_equations": "references_equation edges",
    "referenced_concepts": "references_concept edges",
    "referenced_validation_rules": "references_validation_rule edges",
    "engineering_intent": "Flow guidance / presentation layer",
    "trace": "Execution trace / API response (runtime)",
    "report": "Report layer",
    "ai_hints": "Not authored in knowledge nodes",
    "interactions": "execution sidecar",
    "assumptions": "execution sidecar",
    "provisional_assumptions": "execution sidecar",
    "parameter_defaults": "execution sidecar",
    "inputs": "execution sidecar",
    "depends_on": "execution sidecar or edges with depends_on type",
    "equations": "execution sidecar or references_equation edges",
    "validation_rules": "execution sidecar or references_validation_rule edges",
    "conditions": "execution sidecar",
    "kind": "execution sidecar (execution variant, not metadata.kind)",
    "outputs": "execution sidecar",
    "lookups": "execution sidecar or references_lookup edges",
    "notes": "execution sidecar (authoring notes, non-executable)",
    "subsections": "execution sidecar",
    "nomenclature": "{id}.nomenclature.yaml or {id}/nomenclature.yaml",
}

# Registered external/unmodeled paragraph references (INFO when cited, not in repo index).
EXTERNAL_UNMODELED_REF_REGISTRY: frozenset[str] = frozenset(
    {
        "328.5.4",
        "300.2",
        "303",
        "Appendix-J",
    }
)

RESOLVED_REFERENCE_EDGE_TYPES: frozenset[str] = frozenset(
    {
        "references_equation",
        "references_lookup",
        "references_table",
        "references_validation_rule",
        "introduces_parameter",
        "depends_on",
    }
)

VALIDATOR_FORBIDDEN_FRONTMATTER_KEYS: frozenset[str] = (
    FORBIDDEN_RUNTIME_STATE_KEYS | FORBIDDEN_PARAGRAPH_FRONTMATTER
)


def sidecar_only_severity() -> Severity:
    return "FAIL" if SIDECAR_ONLY_ENFORCEMENT == "fail" else "WARN"


def _format_destination(key: str, node_id: str) -> str:
    dest = KEY_PERMITTED_DESTINATIONS.get(key, f"{node_id}.execution.yaml")
    return dest.replace("{id}", node_id) if node_id else dest


def _present_value(meta: dict[str, Any], key: str) -> bool:
    if key not in meta:
        return False
    value = meta[key]
    if value is None:
        return False
    if isinstance(value, (list, dict, str)) and not value:
        return False
    return True


def check_paragraph_frontmatter_placement(
    meta: dict[str, Any],
    *,
    node_id: str = "",
) -> list[tuple[Severity, str]]:
    """Return placement findings for paragraph frontmatter (FAIL/WARN only)."""
    findings: list[tuple[Severity, str]] = []
    nid = node_id or str(meta.get("id") or "")

    for key in sorted(FORBIDDEN_RUNTIME_STATE_KEYS):
        if key in meta:
            dest = _format_destination(key, nid)
            findings.append(("FAIL", f"forbidden field: {key} (permitted destination: {dest})"))

    for key in sorted(FORBIDDEN_PARAGRAPH_FRONTMATTER):
        if key in meta:
            dest = _format_destination(key, nid)
            findings.append(("FAIL", f"forbidden field: {key} (belongs in {dest})"))

    sidecar_severity = sidecar_only_severity()
    for key in sorted(SIDECAR_ONLY_KEYS):
        if key in FORBIDDEN_PARAGRAPH_FRONTMATTER:
            continue
        if not _present_value(meta, key):
            continue
        dest = _format_destination(key, nid)
        findings.append(
            (
                sidecar_severity,
                f"{key} belongs in {dest}; migration required",
            )
        )

    return findings


def check_paragraph_frontmatter_migration(
    meta: dict[str, Any],
    *,
    node_id: str = "",
) -> list[tuple[Severity, str]]:
    """WARN-level SIDECAR_ONLY migration findings for audit (after validator FAIL checks)."""
    findings: list[tuple[Severity, str]] = []
    nid = node_id or str(meta.get("id") or "")

    if SIDECAR_ONLY_ENFORCEMENT == "fail":
        return check_paragraph_frontmatter_placement(meta, node_id=nid)

    sidecar_severity = sidecar_only_severity()
    for key in sorted(SIDECAR_ONLY_KEYS):
        if key in FORBIDDEN_PARAGRAPH_FRONTMATTER:
            continue
        if not _present_value(meta, key):
            continue
        dest = _format_destination(key, nid)
        findings.append(
            (
                sidecar_severity,
                f"{key} belongs in {dest}; migration required",
            )
        )

    return findings


def check_paragraph_sidecar_surface(
    frontmatter: dict[str, Any],
    sidecar_data: dict[str, Any],
    *,
    node_id: str,
) -> list[tuple[Severity, str]]:
    """Detect duplicate keys or split execution metadata across frontmatter and sidecar."""
    findings: list[tuple[Severity, str]] = []
    sidecar_label = f"{node_id}.execution.yaml"

    fm_keys = {k for k in SIDECAR_ONLY_KEYS if _present_value(frontmatter, k)}
    sc_keys = {k for k in SIDECAR_ONLY_KEYS if _present_value(sidecar_data, k)}
    overlap = fm_keys & sc_keys

    for key in sorted(overlap):
        if key in FORBIDDEN_PARAGRAPH_FRONTMATTER:
            findings.append(
                (
                    "FAIL",
                    f"Duplicate authoring surface: {key!r} appears in frontmatter and "
                    f"{sidecar_label}; use sidecar only",
                )
            )
        else:
            sev = sidecar_only_severity()
            findings.append(
                (
                    sev,
                    f"Duplicate authoring surface: {key!r} appears in frontmatter and "
                    f"{sidecar_label}; use sidecar only",
                )
            )

    fm_only = fm_keys - sc_keys
    sc_only = sc_keys - fm_keys
    if fm_only and sc_only:
        findings.append(
            (
                "WARN",
                "Execution metadata split across two authoring surfaces: "
                f"frontmatter has {sorted(fm_only)}; sidecar has {sorted(sc_only)}; "
                "consolidate into sidecar",
            )
        )

    return findings


def classify_edge_target(
    target: str,
    edge_type: str,
    *,
    repo_index: set[str],
    external_registry: frozenset[str] | None = None,
) -> list[tuple[Severity, str]]:
    """Classify an edge target against the repo index and external registry."""
    registry = external_registry if external_registry is not None else EXTERNAL_UNMODELED_REF_REGISTRY
    cleaned = str(target or "").strip()
    if not cleaned:
        return [("FAIL", "malformed edge target: empty")]

    if cleaned in repo_index:
        return []

    if cleaned in registry:
        return [
            (
                "INFO",
                f"registered external/unmodeled reference: {cleaned}",
            )
        ]

    if edge_type in RESOLVED_REFERENCE_EDGE_TYPES:
        return [("FAIL", f"broken resolved reference: {cleaned}")]

    if edge_type == "related_to":
        return [
            (
                "WARN",
                f"unresolved related_to target: {cleaned} — register or author node",
            )
        ]

    return [("WARN", f"edge target not in repository index: {cleaned}")]


def validator_fail_messages_for_frontmatter(meta: dict[str, Any]) -> list[str]:
    """Messages for validate_paragraph_node — FAIL-level placement only."""
    messages: list[str] = []
    for key in sorted(VALIDATOR_FORBIDDEN_FRONTMATTER_KEYS):
        if key in meta:
            messages.append(f"forbidden field: {key}")

    if SIDECAR_ONLY_ENFORCEMENT == "fail":
        for key in sorted(SIDECAR_ONLY_KEYS):
            if key in FORBIDDEN_PARAGRAPH_FRONTMATTER:
                continue
            if _present_value(meta, key):
                dest = _format_destination(key, str(meta.get("id") or ""))
                messages.append(f"forbidden field: {key} (belongs in {dest})")

    return messages
