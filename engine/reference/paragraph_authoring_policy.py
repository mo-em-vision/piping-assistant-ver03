"""Canonical field-placement policy for paragraph node primary YAML.

Authors maintain one ``{id}.yaml`` file. Node-owned execution metadata lives in the
nested ``execution`` block (or legacy sidecar during compatibility phase).
"""

from __future__ import annotations

from typing import Any, Literal

from engine.reference.node_authoring_policy import (
    FORBIDDEN_RUNTIME_STATE_KEYS,
    present_value,
)

Severity = Literal["FAIL", "WARN", "INFO"]

# Top-level execution keys must live under ``execution`` (FAIL immediately).
EXECUTION_BLOCK_ENFORCEMENT: Literal["warn", "fail"] = "fail"

FORBIDDEN_PARAGRAPH_FRONTMATTER: frozenset[str] = frozenset(
    {
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

EXECUTION_BLOCK_KEYS: frozenset[str] = frozenset(EXECUTION_SIDECAR_KEYS)

# Backward-compatible alias used by sidecar loader and audit inventory.
SIDECAR_ONLY_KEYS: frozenset[str] = frozenset(
    {*EXECUTION_SIDECAR_KEYS, NOMENCLATURE_SIDECAR_KEY}
)

# Deprecated: use EXECUTION_BLOCK_ENFORCEMENT.
SIDECAR_ONLY_ENFORCEMENT: Literal["warn", "fail"] = EXECUTION_BLOCK_ENFORCEMENT

PARAGRAPH_PERMITTED_TOP_LEVEL: frozenset[str] = frozenset(
    {
        "id",
        "type",
        "key",
        "title",
        "authority",
        "edition",
        "paragraph_number",
        "text",
        "hierarchy",
        "presentation",
        "metadata",
        "edges",
        "execution",
        NOMENCLATURE_SIDECAR_KEY,
    }
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
    "applicability": "execution block in primary YAML",
    "paragraph_class": "metadata.kind or typed edges",
    "limitations": "execution block or text.original",
    "exceptions": "execution block or text.original",
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
    "interactions": "execution block in primary YAML",
    "assumptions": "execution block in primary YAML",
    "provisional_assumptions": "execution block in primary YAML",
    "parameter_defaults": "execution block in primary YAML",
    "inputs": "execution block in primary YAML",
    "depends_on": "execution block or edges with depends_on type",
    "equations": "execution block or references_equation edges",
    "validation_rules": "execution block or references_validation_rule edges",
    "conditions": "execution block in primary YAML",
    "kind": "execution block (execution variant, not metadata.kind)",
    "outputs": "execution block in primary YAML",
    "lookups": "execution block or references_lookup edges",
    "notes": "execution block (authoring notes, non-executable)",
    "subsections": "execution block in primary YAML",
    "nomenclature": "nomenclature block or introduces_parameter edges",
}

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


def execution_block_severity() -> Severity:
    return "FAIL" if EXECUTION_BLOCK_ENFORCEMENT == "fail" else "WARN"


def sidecar_only_severity() -> Severity:
    return execution_block_severity()


def _format_destination(key: str, node_id: str) -> str:
    dest = KEY_PERMITTED_DESTINATIONS.get(key, "execution block in primary YAML")
    return dest.replace("{id}", node_id) if node_id else dest


def _execution_block(meta: dict[str, Any]) -> dict[str, Any]:
    block = meta.get("execution")
    return block if isinstance(block, dict) else {}


def check_execution_block_schema(meta: dict[str, Any]) -> list[tuple[Severity, str]]:
    block = _execution_block(meta)
    if not block:
        return []
    findings: list[tuple[Severity, str]] = []
    for key in sorted(block):
        if key not in EXECUTION_BLOCK_KEYS:
            findings.append(
                (
                    "FAIL",
                    f"unknown key in execution block: {key}",
                )
            )
    return findings


def check_paragraph_frontmatter_placement(
    meta: dict[str, Any],
    *,
    node_id: str = "",
) -> list[tuple[Severity, str]]:
    """Return placement findings for paragraph primary YAML (FAIL/WARN only)."""
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

    block_severity = execution_block_severity()
    for key in sorted(EXECUTION_BLOCK_KEYS):
        if not present_value(meta, key):
            continue
        dest = _format_destination(key, nid)
        findings.append(
            (
                block_severity,
                f"{key} belongs in {dest}; migration required",
            )
        )

    findings.extend(check_execution_block_schema(meta))
    return findings


def check_paragraph_frontmatter_migration(
    meta: dict[str, Any],
    *,
    node_id: str = "",
) -> list[tuple[Severity, str]]:
    """Migration findings for audit (top-level execution keys outside execution block)."""
    return check_paragraph_frontmatter_placement(meta, node_id=node_id)


def check_paragraph_sidecar_surface(
    frontmatter: dict[str, Any],
    sidecar_data: dict[str, Any],
    *,
    node_id: str,
) -> list[tuple[Severity, str]]:
    """Detect duplicate keys or split metadata across primary YAML and legacy sidecar."""
    findings: list[tuple[Severity, str]] = []
    sidecar_label = f"{node_id}.execution.yaml (legacy)"

    execution_block = _execution_block(frontmatter)
    block_keys = {k for k in EXECUTION_BLOCK_KEYS if present_value(execution_block, k)}
    top_keys = {k for k in EXECUTION_BLOCK_KEYS if present_value(frontmatter, k)}
    fm_keys = block_keys | top_keys
    sc_keys = {k for k in EXECUTION_BLOCK_KEYS if present_value(sidecar_data, k)}
    overlap = fm_keys & sc_keys

    for key in sorted(overlap):
        sev = execution_block_severity()
        findings.append(
            (
                sev,
                f"Duplicate authoring surface: {key!r} appears in primary YAML and "
                f"{sidecar_label}; consolidate into execution block",
            )
        )

    fm_only = fm_keys - sc_keys
    sc_only = sc_keys - fm_keys
    if fm_only and sc_only:
        findings.append(
            (
                "WARN",
                "Execution metadata split across two authoring surfaces: "
                f"primary YAML has {sorted(fm_only)}; legacy sidecar has {sorted(sc_only)}; "
                "consolidate into execution block",
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

    for key in sorted(EXECUTION_BLOCK_KEYS):
        if present_value(meta, key):
            dest = _format_destination(key, str(meta.get("id") or ""))
            messages.append(f"forbidden field: {key} (belongs in {dest})")

    for level, msg in check_execution_block_schema(meta):
        if level == "FAIL":
            messages.append(msg)

    return messages
