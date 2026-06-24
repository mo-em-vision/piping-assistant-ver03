"""Resolve user-facing material tokens to canonical material_id keys in standards tables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.material_catalog_db import resolve_material_id
from engine.reference.material_ids import (
    ASTM_A106_GR_B,
    ASME_SA_105,
    is_material_id,
)

# Legacy labels from older task sessions and docs.
_LEGACY_TO_MATERIAL_ID: dict[str, str] = {
    "A106B": ASTM_A106_GR_B,
    "SA106B": ASTM_A106_GR_B,
    "A106-B": ASTM_A106_GR_B,
    "A106GRB": ASTM_A106_GR_B,
    "A106GRADEB": ASTM_A106_GR_B,
    "SA106GRB": ASTM_A106_GR_B,
    "ASTMA106GRADEB": ASTM_A106_GR_B,
    "A106 GR B": ASTM_A106_GR_B,
    "SA-106B": ASTM_A106_GR_B,
    "SA-106 B": ASTM_A106_GR_B,
    "SA-106 GRADE B": ASTM_A106_GR_B,
    "SA105": ASME_SA_105,
    "SA-105": ASME_SA_105,
}


def normalize_material_token(material: str) -> str:
    return material.strip().upper().replace(" ", "")


def canonical_material_id(
    material: str,
    *,
    standards_root: Path | None = None,
) -> str | None:
    """Resolve any catalog alias or legacy label to a canonical material_id."""
    cleaned = material.strip()
    if not cleaned:
        return None

    if is_material_id(cleaned):
        return cleaned

    if standards_root is not None:
        resolved = resolve_material_id(standards_root, cleaned)
        if resolved is not None:
            return resolved

    legacy = _LEGACY_TO_MATERIAL_ID.get(cleaned) or _LEGACY_TO_MATERIAL_ID.get(cleaned.upper())
    if legacy is not None:
        return legacy

    normalized = normalize_material_token(cleaned)
    return _LEGACY_TO_MATERIAL_ID.get(normalized)


def resolve_material_table_key(
    materials: dict[str, Any],
    material: str,
    *,
    standards_root: Path | None = None,
) -> str | None:
    """Match a material token to a key in a standards table materials dict."""
    if not material or not materials:
        return None

    if material in materials:
        return material

    material_id = canonical_material_id(material, standards_root=standards_root)
    if material_id is not None and material_id in materials:
        return material_id

    normalized = normalize_material_token(material)
    for key in materials:
        if normalize_material_token(str(key)) == normalized:
            return str(key)

    return None
