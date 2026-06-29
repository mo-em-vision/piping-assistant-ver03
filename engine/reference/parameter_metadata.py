"""Parameter node metadata helpers (no graph store dependency)."""

from __future__ import annotations

from typing import Any

from engine.units.unit_ids import symbol_from_unit_id, unit_id_from_legacy_symbol


def parameter_defined_in(metadata: dict[str, Any]) -> tuple[str, ...]:
    """Section or definition nodes where this parameter symbol is introduced."""
    defined = metadata.get("defined_in")
    if isinstance(defined, str) and defined.strip():
        return (defined.strip(),)
    if isinstance(defined, list):
        nodes = [str(item).strip() for item in defined if str(item).strip()]
        if nodes:
            return tuple(nodes)
    located = metadata.get("located_in")
    if isinstance(located, str) and located.strip():
        return (located.strip(),)
    if isinstance(located, list):
        nodes = [str(item).strip() for item in located if str(item).strip()]
        if nodes:
            return tuple(nodes)
    return ()


def parameter_concept_id(metadata: dict[str, Any]) -> str | None:
    """Shared engineering concept id when multiple parameter nodes are aliases."""
    concept = metadata.get("concept_id") or metadata.get("concept")
    if concept is None:
        return None
    text = str(concept).strip()
    return text or None


def normalize_allowed_units(metadata: dict[str, Any]) -> list[str]:
    """Normalize parameter allowed_units to canonical UNIT-* ids."""
    raw = metadata.get("allowed_units")
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not item:
            continue
        text = str(item).strip()
        if not text:
            continue
        unit_id = text if text.startswith("UNIT-") else unit_id_from_legacy_symbol(text)
        if unit_id and unit_id not in seen:
            seen.add(unit_id)
            normalized.append(unit_id)
    return normalized


def prepare_parameter_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Normalize parameter node metadata at graph compile time."""
    meta = dict(metadata)
    meta.pop("priority", None)

    canonical = meta.get("canonical_unit")
    legacy_unit = meta.get("unit")
    if canonical:
        canonical_text = str(canonical).strip()
        meta["canonical_unit"] = canonical_text
        if not legacy_unit:
            meta["unit"] = symbol_from_unit_id(canonical_text)
    elif legacy_unit is not None:
        unit_id = unit_id_from_legacy_symbol(str(legacy_unit))
        if unit_id:
            meta["canonical_unit"] = unit_id

    defined = parameter_defined_in(meta)
    if defined:
        meta["defined_in"] = list(defined)
        meta.setdefault("located_in", list(defined))
    return meta
