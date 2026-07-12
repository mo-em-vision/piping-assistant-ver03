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


def validator_fail_messages_for_workflow(meta: dict[str, Any]) -> list[str]:
    return [msg for level, msg in check_workflow_frontmatter_placement(meta) if level == "FAIL"]
