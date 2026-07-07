"""Equation node citation helpers for standards equation nodes."""

from __future__ import annotations

import re
from typing import Any

_EQ_NUMBER_FROM_ID = re.compile(r"-eq-(.+)$")


def equation_reference(metadata: dict[str, Any]) -> str:
    """Return the standards equation number for display and provenance."""
    explicit = str(metadata.get("equation_number") or "").strip()
    if explicit:
        return explicit

    legacy = metadata.get("metadata") or {}
    if isinstance(legacy, dict):
        legacy_id = str(legacy.get("legacy_equation_id") or "").strip()
        if legacy_id.startswith("eq-"):
            return legacy_id.removeprefix("eq-")

    node_id = str(metadata.get("id") or "").strip()
    match = _EQ_NUMBER_FROM_ID.search(node_id)
    if match:
        return match.group(1)

    runtime_id = str(metadata.get("equation_id") or "").strip()
    if runtime_id.startswith("eq-"):
        return runtime_id.removeprefix("eq-")

    return ""


def equation_paragraph_reference(metadata: dict[str, Any]) -> str:
    """Return governing paragraph citation for an equation node, if authored."""
    explicit = str(metadata.get("paragraph_number") or "").strip()
    if explicit:
        return explicit

    legacy = str(metadata.get("paragraph") or "").strip()
    if legacy:
        return legacy.split(",", 1)[0].strip()

    authority = metadata.get("authority") or {}
    if isinstance(authority, dict):
        authorized = authority.get("authorized_by") or []
        if authorized:
            first = str(authorized[0]).strip()
            if first:
                return first

    nomenclature_ref = str(metadata.get("nomenclature_ref") or "").strip()
    if nomenclature_ref and nomenclature_ref[0].isdigit():
        return nomenclature_ref

    return ""


def format_equation_citation(
    *,
    standard_label: str,
    equation_number: str,
    paragraph_number: str | None = None,
) -> str:
    label = equation_number.strip()
    if not label:
        return standard_label
    eq_label = f"Eq. ({label})"
    if paragraph_number:
        return f"{standard_label} {eq_label} (para. {paragraph_number})"
    return f"{standard_label} {eq_label}"
