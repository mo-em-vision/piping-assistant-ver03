"""Legacy display-role migration rules — test and one-time script only."""

from __future__ import annotations

from typing import Any

from models.display_role import (
    DisplayRole,
    DisplayState,
    EquationContent,
    infer_equation_content,
    is_canonical_display_role,
)

LEGACY_DISPLAY_ROLE_ALIASES: dict[str, str] = {
    "calculation_trace": DisplayRole.equation.value,
    "equation_trace": DisplayRole.equation.value,
    "preview": DisplayRole.equation.value,
    "equation_preview": DisplayRole.equation.value,
    "activation": DisplayRole.equation.value,
    "node_activation": DisplayRole.equation.value,
    "intro": DisplayRole.node_intro.value,
    "recommendation": DisplayRole.lookup_table_recommendation.value,
    "validation_check": DisplayRole.applicability.value,
    "result": DisplayRole.result_summary.value,
}

LEGACY_EQUATION_STATE: dict[str, str] = {
    "calculation_trace": DisplayState.evaluated.value,
    "equation_trace": DisplayState.evaluated.value,
    "preview": DisplayState.preview.value,
    "equation_preview": DisplayState.preview.value,
    "activation": DisplayState.active.value,
    "node_activation": DisplayState.active.value,
}


def _is_legacy_role(role: str) -> bool:
    return role in LEGACY_DISPLAY_ROLE_ALIASES or role == "substituted"


def migrate_substituted_role(block: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(block)
    migrated["display_role"] = DisplayRole.equation.value
    migrated["display_state"] = DisplayState.preview.value
    migrated["equation_content"] = EquationContent.substituted.value
    migrated.pop("internal_display_role", None)
    return migrated


def migrate_legacy_role_name(role: str, block: dict[str, Any]) -> dict[str, Any]:
    if role == "substituted":
        return migrate_substituted_role(block)

    migrated = dict(block)
    migrated["display_role"] = LEGACY_DISPLAY_ROLE_ALIASES[role]
    if migrated["display_role"] == DisplayRole.equation.value:
        migrated["display_state"] = LEGACY_EQUATION_STATE.get(role, DisplayState.preview.value)
        if role in {"calculation_trace", "equation_trace"}:
            migrated["equation_content"] = infer_equation_content(migrated)
        else:
            migrated["equation_content"] = infer_equation_content(migrated)
    migrated.pop("internal_display_role", None)
    return migrated


def migrate_display_block_roles(block: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(block, dict):
        return block

    display_role = str(block.get("display_role") or "").strip()
    internal_role = str(block.get("internal_display_role") or "").strip()

    if display_role and is_canonical_display_role(display_role):
        migrated = dict(block)
        migrated.pop("internal_display_role", None)
        return migrated

    if display_role and _is_legacy_role(display_role):
        return migrate_legacy_role_name(display_role, block)

    if display_role and not is_canonical_display_role(display_role):
        migrated = dict(block)
        migrated.pop("internal_display_role", None)
        return migrated

    if internal_role:
        source = dict(block)
        source["display_role"] = internal_role
        source.pop("internal_display_role", None)
        role = internal_role
        if _is_legacy_role(role):
            return migrate_legacy_role_name(role, source)
        if is_canonical_display_role(role):
            return source

    migrated = dict(block)
    migrated.pop("internal_display_role", None)
    return migrated


def migrate_transcript_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    migrated = dict(payload)
    role = str(migrated.get("display_role") or "").strip()
    if not role:
        return migrated
    if is_canonical_display_role(role):
        return migrated
    if _is_legacy_role(role):
        fake_block = {"display_role": role, **migrated}
        result = migrate_legacy_role_name(role, fake_block)
        migrated["display_role"] = result.get("display_role", role)
        if "display_state" in result:
            migrated["display_state"] = result["display_state"]
        if "equation_content" in result:
            migrated["equation_content"] = result["equation_content"]
    elif role in LEGACY_DISPLAY_ROLE_ALIASES:
        migrated["display_role"] = LEGACY_DISPLAY_ROLE_ALIASES[role]
    return migrated


EQUATION_TRACE_KEY_SUFFIX_LEGACY = "equation_trace"
EQUATION_TRACE_KEY_SUFFIX = "equation"


def migrate_equation_trace_key(key: str) -> str:
    parts = str(key or "").split("|")
    if len(parts) == 4 and parts[3] == EQUATION_TRACE_KEY_SUFFIX_LEGACY:
        parts[3] = EQUATION_TRACE_KEY_SUFFIX
        return "|".join(parts)
    return key
