"""Map legacy unit strings to canonical unit node ids."""

from __future__ import annotations

_LEGACY_SYMBOL_TO_UNIT_ID: dict[str, str] = {
    "pa": "UNIT-Pa",
    "psi": "UNIT-psi",
    "bar": "UNIT-bar",
    "mpa": "UNIT-MPa",
    "mm": "UNIT-mm",
    "in": "UNIT-in",
    "inch": "UNIT-in",
    "k": "UNIT-K",
    "f": "UNIT-degF",
    "degf": "UNIT-degF",
    "°f": "UNIT-degF",
    "c": "UNIT-degC",
    "degc": "UNIT-degC",
    "°c": "UNIT-degC",
    "dimensionless": "UNIT-dimensionless",
    "1": "UNIT-dimensionless",
    "": "UNIT-dimensionless",
}

_CANONICAL_SI_UNIT_ID: dict[str, str] = {
    "pressure": "UNIT-Pa",
    "stress": "UNIT-Pa",
    "length": "UNIT-mm",
    "temperature": "UNIT-K",
    "dimensionless": "UNIT-dimensionless",
}

_DIMENSION_ALIASES: dict[str, str] = {
    "stress": "pressure",
}


def normalize_unit_key(unit: str) -> str:
    return unit.strip().lower()


def unit_id_from_legacy_symbol(unit: str) -> str | None:
    """Resolve a legacy unit string or UNIT-* id to a unit node id."""
    text = unit.strip()
    if not text:
        return "UNIT-dimensionless"
    if text.startswith("UNIT-"):
        return text
    return _LEGACY_SYMBOL_TO_UNIT_ID.get(normalize_unit_key(text))


def symbol_from_unit_id(unit_id: str) -> str:
    """Derive legacy display symbol from a unit node id."""
    if unit_id == "UNIT-dimensionless":
        return "dimensionless"
    if unit_id.startswith("UNIT-"):
        return unit_id[5:]
    return unit_id


def normalize_dimension(dimension: str | None) -> str | None:
    """Map quantity dimension keys to registry dimensions."""
    if dimension is None:
        return None
    text = dimension.strip().lower()
    if not text:
        return None
    return _DIMENSION_ALIASES.get(text, text)


def canonical_si_unit_id(dimension: str) -> str | None:
    normalized = normalize_dimension(dimension)
    if normalized is None:
        return None
    return _CANONICAL_SI_UNIT_ID.get(normalized)
