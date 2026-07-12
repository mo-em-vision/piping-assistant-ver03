"""Shared authoring policy primitives for one-primary-YAML-per-node knowledge authoring.

Contracts describe rules for authors; this module is the enforcement source of truth
alongside per-type validators and the audit script.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Severity = Literal["FAIL", "WARN", "INFO"]

# Phase 3: legacy node-owned sidecars are no longer read from disk.
LEGACY_SIDECAR_COMPAT: bool = False

FindingCode = Literal[
    "VALID_PRIMARY_NODE_METADATA",
    "VALID_SHARED_DATASET_REFERENCE",
    "LEGACY_SIDECAR_METADATA",
    "SPLIT_AUTHORING_SURFACE",
    "DUPLICATE_FIELD_DEFINITION",
    "CONFLICTING_FIELD_DEFINITION",
    "FORBIDDEN_RUNTIME_STATE",
    "UNKNOWN_NODE_FIELD",
    "INVALID_NESTED_FIELD",
    "BROKEN_REQUIRED_REFERENCE",
    "NONCANONICAL_LEGACY_FORMAT",
]

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
        "runtime_result",
        "current_phase",
        "active_goal_id",
    }
)

PARAMETER_FORBIDDEN_RUNTIME_KEYS: frozenset[str] = frozenset(
    {
        "value",
        "unit",
        "resolution",
        "source",
        "timestamp",
        "execution_id",
        "workflow_id",
        "status",
    }
)


@dataclass(frozen=True)
class AuthoringFinding:
    severity: Severity
    code: FindingCode
    message: str
    key: str = ""


def present_value(meta: dict[str, Any], key: str) -> bool:
    if key not in meta:
        return False
    value = meta[key]
    if value is None:
        return False
    if isinstance(value, (list, dict, str)) and not value:
        return False
    return True


def check_forbidden_runtime_state(
    meta: dict[str, Any],
    *,
    extra_forbidden: frozenset[str] | None = None,
) -> list[AuthoringFinding]:
    forbidden = FORBIDDEN_RUNTIME_STATE_KEYS | (extra_forbidden or frozenset())
    findings: list[AuthoringFinding] = []
    for key in sorted(forbidden):
        if key in meta:
            findings.append(
                AuthoringFinding(
                    severity="FAIL",
                    code="FORBIDDEN_RUNTIME_STATE",
                    message=f"forbidden runtime field: {key}",
                    key=key,
                )
            )
    return findings


def values_conflict(a: Any, b: Any) -> bool:
    return a != b


def check_duplicate_nested_vs_top_level(
    meta: dict[str, Any],
    *,
    nested_block: str,
    nested_keys: frozenset[str],
    node_id: str,
) -> list[AuthoringFinding]:
    """Detect duplicate or conflicting definitions across nested block and top level."""
    findings: list[AuthoringFinding] = []
    block = meta.get(nested_block)
    if not isinstance(block, dict):
        return findings

    for key in nested_keys:
        if not present_value(meta, key):
            continue
        if key not in block or not present_value(block, key):
            findings.append(
                AuthoringFinding(
                    severity="FAIL",
                    code="SPLIT_AUTHORING_SURFACE",
                    message=(
                        f"{key!r} split across top level and {nested_block} block "
                        f"for node {node_id}; consolidate under {nested_block}"
                    ),
                    key=key,
                )
            )
            continue
        if values_conflict(meta[key], block[key]):
            findings.append(
                AuthoringFinding(
                    severity="FAIL",
                    code="CONFLICTING_FIELD_DEFINITION",
                    message=(
                        f"conflicting {key!r} in top level and {nested_block} block "
                        f"for node {node_id}"
                    ),
                    key=key,
                )
            )
        else:
            findings.append(
                AuthoringFinding(
                    severity="FAIL",
                    code="DUPLICATE_FIELD_DEFINITION",
                    message=(
                        f"duplicate {key!r} in top level and {nested_block} block "
                        f"for node {node_id}; keep {nested_block} only"
                    ),
                    key=key,
                )
            )
    return findings
