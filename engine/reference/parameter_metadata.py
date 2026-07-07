"""Parameter node metadata helpers (no graph store dependency)."""

from __future__ import annotations

from typing import Any

from engine.units.unit_ids import symbol_from_unit_id, unit_id_from_legacy_symbol

_NESTED_PARAMETER_META_KEYS = frozenset(
    {
        "allowed_units",
        "canonical_unit",
        "unit",
        "composer_input",
        "composer_options",
        "default",
        "default_value",
    }
)


def _merge_nested_parameter_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Lift composer/runtime fields from nested ``metadata:`` blocks on PARAM nodes."""
    merged = dict(metadata)
    nested = metadata.get("metadata")
    if not isinstance(nested, dict):
        return merged
    for key in _NESTED_PARAMETER_META_KEYS:
        if key in nested and key not in merged:
            merged[key] = nested[key]
    return merged


def _parameter_dimension_id(metadata: dict[str, Any]) -> str | None:
    dimension = metadata.get("dimension")
    if isinstance(dimension, str) and dimension.strip().startswith("DIM-"):
        return dimension.strip()
    for edge in metadata.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("type") or "") != "has_dimension":
            continue
        target = str(edge.get("target") or "").strip()
        if target.startswith("DIM-"):
            return target
    return None


def _enrich_parameter_from_dimension(metadata: dict[str, Any]) -> dict[str, Any]:
    """Copy canonical unit and allowed units from a referenced global dimension node."""
    meta = dict(metadata)
    if meta.get("canonical_unit") or meta.get("unit"):
        return meta
    dimension_id = _parameter_dimension_id(meta)
    if not dimension_id:
        return meta

    from engine.reference.graph_edge_schema import dimension_allowed_unit_ids
    from engine.reference.nomenclature_resolver import _load_dimension_node

    dim_meta = _load_dimension_node(dimension_id)
    if dim_meta is None:
        return meta

    raw_canonical = dim_meta.get("canonical_unit")
    if raw_canonical is not None:
        canonical = str(raw_canonical).strip()
        if canonical and canonical.lower() != "null":
            meta.setdefault("canonical_unit", canonical)

    if not meta.get("allowed_units"):
        allowed = dimension_allowed_unit_ids(dim_meta)
        if allowed:
            meta["allowed_units"] = allowed

    return meta


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
    introduced = metadata.get("introduced_by")
    if isinstance(introduced, str) and introduced.strip():
        return (introduced.strip(),)
    if isinstance(introduced, list):
        nodes = [str(item).strip() for item in introduced if str(item).strip()]
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
    meta = _merge_nested_parameter_metadata(metadata)
    meta.pop("priority", None)

    if not str(meta.get("symbol") or "").strip():
        canonical_symbol = str(meta.get("canonical_symbol") or "").strip()
        if canonical_symbol:
            meta["symbol"] = canonical_symbol
    if not str(meta.get("title") or "").strip():
        name = str(meta.get("name") or "").strip()
        if name:
            meta["title"] = name

    meta = _enrich_parameter_from_dimension(meta)

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
