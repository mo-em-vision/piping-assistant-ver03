"""Canonical NPS/DN normalization for ASME B36.10 pipe dimension lookups."""

from __future__ import annotations

from models.fact import Fact, fact_unit

# ISO 6708 / common DN to ASME B36.10 NPS keys used in the dimension tables.
_DN_TO_NPS: dict[str, str] = {
    "6": "1/8",
    "8": "1/4",
    "10": "3/8",
    "15": "1/2",
    "20": "3/4",
    "25": "1",
    "32": "1-1/4",
    "40": "1-1/2",
    "50": "2",
    "65": "2-1/2",
    "80": "3",
    "100": "4",
    "125": "5",
    "150": "6",
    "200": "8",
    "250": "10",
    "300": "12",
    "350": "14",
    "400": "16",
}


def normalize_entry_unit(unit: str | None) -> str:
    text = (unit or "NPS").strip().upper()
    if text in {"NPS", "DN"}:
        return text
    if text in {"IN", "INCH", "INCHES"}:
        return "NPS"
    if text in {"DIMENSIONLESS", "1", ""}:
        return "NPS"
    raise ValueError(f"Unsupported nominal pipe size unit: {unit}")


def nps_entry_unit(fact: Fact) -> str:
    if fact.original_unit:
        return normalize_entry_unit(fact.original_unit)
    return normalize_entry_unit(fact_unit(fact))


def to_nps_lookup_key(value: str, unit: str) -> str:
    text = str(value).strip().strip('"').strip("'")
    if not text:
        raise ValueError("Nominal pipe size is required.")

    if unit == "DN":
        dn = text.upper().replace("DN", "").strip()
        mapped = _DN_TO_NPS.get(dn)
        if mapped is None:
            raise ValueError(
                f"DN size {value!r} is not recognized. "
                "Enter a standard DN value (for example 50, 100, or 150)."
            )
        return mapped

    return text
