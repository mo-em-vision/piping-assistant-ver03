"""Authoring policy for equation and validation_rule primary YAML.

Equations may keep execution metadata at top level (existing one-file inline pattern)
or under nested ``definition`` / ``execution`` blocks. Duplicate placement fails.
"""

from __future__ import annotations

from typing import Any, Literal

from engine.reference.node_authoring_policy import FORBIDDEN_RUNTIME_STATE_KEYS, present_value

Severity = Literal["FAIL", "WARN", "INFO"]

EQUATION_EXECUTION_BLOCK = "execution"
EQUATION_DEFINITION_BLOCK = "definition"

EQUATION_EXECUTION_KEYS: frozenset[str] = frozenset(
    {
        "variables",
        "steps",
        "executor",
        "execution_function",
        "calculation_module",
        "outputs",
        "equation_id",
        "nomenclature_ref",
        "display",
        "applies_when",
        "paragraph",
        "assumptions",
        "interactions",
        "provisional_assumptions",
    }
)

EQUATION_DEFINITION_KEYS: frozenset[str] = frozenset(
    {
        "expression",
        "executor",
        "execution_function",
        "calculation_module",
        "calculation_kind",
        "conversion",
    }
)


def _block(meta: dict[str, Any], name: str) -> dict[str, Any]:
    block = meta.get(name)
    return block if isinstance(block, dict) else {}


def check_equation_frontmatter_placement(meta: dict[str, Any]) -> list[tuple[Severity, str]]:
    findings: list[tuple[Severity, str]] = []
    for key in sorted(FORBIDDEN_RUNTIME_STATE_KEYS):
        if key in meta:
            findings.append(("FAIL", f"forbidden field: {key}"))

    definition_block = _block(meta, EQUATION_DEFINITION_BLOCK)
    execution_block = _block(meta, EQUATION_EXECUTION_BLOCK)

    for key in sorted(EQUATION_DEFINITION_KEYS):
        if present_value(meta, key) and present_value(definition_block, key):
            findings.append(
                (
                    "FAIL",
                    f"duplicate {key!r} in top level and {EQUATION_DEFINITION_BLOCK} block",
                )
            )

    for key in sorted(EQUATION_EXECUTION_KEYS):
        if present_value(meta, key) and present_value(execution_block, key):
            findings.append(
                (
                    "FAIL",
                    f"duplicate {key!r} in top level and {EQUATION_EXECUTION_BLOCK} block",
                )
            )

    for block_name, allowed in (
        (EQUATION_DEFINITION_BLOCK, EQUATION_DEFINITION_KEYS),
        (EQUATION_EXECUTION_BLOCK, EQUATION_EXECUTION_KEYS),
    ):
        block = _block(meta, block_name)
        for key in sorted(block):
            if key not in allowed:
                findings.append(("FAIL", f"unknown key in {block_name} block: {key}"))
    return findings


def validator_fail_messages_for_equation(meta: dict[str, Any]) -> list[str]:
    return [msg for level, msg in check_equation_frontmatter_placement(meta) if level == "FAIL"]
