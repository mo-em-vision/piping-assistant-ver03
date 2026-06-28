"""Canonical material identifiers shared across engineering standards tables."""

from __future__ import annotations

import re

# Sample catalog ids used in development seeds and B31.3 lookup tables.
ASTM_A53 = "astm_a53"
ASTM_A105 = "astm_a105"
ASTM_A106_GR_A = "astm_a106_gr_a"
ASTM_A106_GR_B = "astm_a106_gr_b"
ASTM_A106_GR_C = "astm_a106_gr_c"
API_5L = "api_5l"
ASTM_A351 = "astm_a351"
ASTM_A451 = "astm_a451"
ASTM_A487 = "astm_a487"

_ID_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def make_material_id(standard_slug: str, grade_key: str) -> str:
    """Build a stable material id from a standards pack slug and grade label."""
    slug = _normalize_slug_part(standard_slug)
    grade = _normalize_slug_part(grade_key)
    tail = slug.rsplit("_", 1)[-1]
    if grade.startswith(f"{tail}_"):
        grade = grade[len(tail) + 1 :]
    elif grade == tail:
        grade = "default"
    return f"{slug}_{grade}" if grade else slug


def _normalize_slug_part(value: str) -> str:
    lowered = value.strip().lower().replace("-", "_").replace(" ", "_")
    cleaned = _ID_SLUG_RE.sub("_", lowered)
    return re.sub(r"_+", "_", cleaned).strip("_")


def is_material_id(token: str) -> bool:
    """Return True when the token looks like a catalog material id."""
    cleaned = token.strip().lower()
    return bool(cleaned) and " " not in cleaned and cleaned.count("_") >= 2
