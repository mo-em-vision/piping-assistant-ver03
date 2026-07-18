"""Authoring policy for workflow primary YAML with nested runtime block."""

from __future__ import annotations

from typing import Any, Literal

from engine.reference.node_authoring_policy import FORBIDDEN_RUNTIME_STATE_KEYS, present_value

Severity = Literal["FAIL", "WARN", "INFO"]

WORKFLOW_RUNTIME_BLOCK = "runtime"
WORKFLOW_RUNTIME_KEYS: frozenset[str] = frozenset(
    {
        "navigation",
        "assumptions",
        "interactions",
        "provisional_assumptions",
        "inputs",
        "equations",
        "conditions",
        "nomenclature",
        "texts",
        "documentation",
        "suggested_workflows",
        "goal_output",
        "engineering_intent",
        "slug",
        "title",
        "purpose",
        "status",
        "version",
    }
)

WORKFLOW_FORBIDDEN_TOP_LEVEL: frozenset[str] = frozenset(WORKFLOW_RUNTIME_KEYS)


def _runtime_block(meta: dict[str, Any]) -> dict[str, Any]:
    block = meta.get(WORKFLOW_RUNTIME_BLOCK)
    return block if isinstance(block, dict) else {}


def check_workflow_frontmatter_placement(meta: dict[str, Any]) -> list[tuple[Severity, str]]:
    findings: list[tuple[Severity, str]] = []
    for key in sorted(FORBIDDEN_RUNTIME_STATE_KEYS):
        if key in meta:
            findings.append(("FAIL", f"forbidden field: {key}"))
    for key in sorted(WORKFLOW_FORBIDDEN_TOP_LEVEL):
        if present_value(meta, key):
            findings.append(
                (
                    "FAIL",
                    f"{key} belongs in runtime block in primary YAML; migration required",
                )
            )
    runtime = _runtime_block(meta)
    for key in sorted(runtime):
        if key not in WORKFLOW_RUNTIME_KEYS:
            findings.append(("FAIL", f"unknown key in runtime block: {key}"))
    return findings


_NAV_PHASE_KEYS = (
    "expansion_assumptions",
    "path_decisions",
    "parameter_gathering",
    "coefficient_resolution",
    "execution_assumptions",
    "definition_equation_completion",
)


def check_workflow_conditionals(meta: dict[str, Any]) -> list[tuple[Severity, str]]:
    """Reject branch gates and parameter lists authored on workflow YAML."""
    findings: list[tuple[Severity, str]] = []
    runtime = _runtime_block(meta)
    navigation = runtime.get("navigation")
    if isinstance(navigation, dict):
        gate_fields = navigation.get("assumption_gate_fields") or []
        if gate_fields:
            findings.append(
                (
                    "FAIL",
                    "runtime.navigation.assumption_gate_fields must be empty; "
                    "author expansion gates on paragraph/equation graph nodes",
                )
            )
        phases = navigation.get("phases") or {}
        if isinstance(phases, dict):
            for phase_key, fields in phases.items():
                if fields:
                    findings.append(
                        (
                            "FAIL",
                            f"runtime.navigation.phases.{phase_key} must be empty; "
                            "graph expansion owns active parameter lists",
                        )
                    )
    interactions = runtime.get("interactions") or []
    if interactions:
        findings.append(
            (
                "FAIL",
                "runtime.interactions must not be authored; "
                "use graph node assumptions and PARAM metadata",
            )
        )
    assumptions = runtime.get("assumptions") or []
    if assumptions:
        findings.append(
            (
                "FAIL",
                "runtime.assumptions must not be authored; "
                "use graph node execution.assumptions",
            )
        )
    return findings


def validator_fail_messages_for_workflow(meta: dict[str, Any]) -> list[str]:
    findings = check_workflow_frontmatter_placement(meta)
    findings.extend(check_workflow_conditionals(meta))
    return [msg for level, msg in findings if level == "FAIL"]
