"""Shared constants and helpers for AI agents."""

from __future__ import annotations

import re

PIPE_WALL_THICKNESS_DESIGN = "pipe_wall_thickness_design"

CONTEXT_KEYWORDS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bweather\b", re.IGNORECASE),
    re.compile(r"\btoday\b", re.IGNORECASE),
    re.compile(r"\bjoke\b", re.IGNORECASE),
)

INSPECTION_KEYWORDS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\binspect\b", re.IGNORECASE),
    re.compile(r"\binspection\b", re.IGNORECASE),
    re.compile(r"\bfitness[\s-]for[\s-]service\b", re.IGNORECASE),
)

MISSING_CONTEXT_PATTERNS: dict[str, re.Pattern[str]] = {
    "design_pressure": re.compile(
        r"\b\d+(?:\.\d+)?\s*(psi|bar|pa|kpa|mpa|barg)\b",
        re.IGNORECASE,
    ),
    "outside_diameter": re.compile(
        r"\b(?:\d+(?:\.\d+)?\s*(?:in|mm|inch(?:es)?)|"
        r"(?:outside\s+)?(?:diameter|od|nps)\s*[:=]?\s*\d+(?:\.\d+)?)\b",
        re.IGNORECASE,
    ),
    "material": re.compile(r"\b(astm|a106|a53|material|grade)\b", re.IGNORECASE),
    "design_temperature": re.compile(
        r"\b\d+(?:\.\d+)?\s*(?:°?\s*[fc]|celsius|celcius|fahrenheit)\b",
        re.IGNORECASE,
    ),
}


def detect_missing_context(message: str) -> list[str]:
    missing: list[str] = []
    for field, pattern in MISSING_CONTEXT_PATTERNS.items():
        if not pattern.search(message):
            missing.append(field)
    return missing
