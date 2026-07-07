"""Shared constants and helpers for AI agents."""

from __future__ import annotations

import re

PIPE_WALL_THICKNESS_DESIGN = "pipe_wall_thickness_design"

PIPE_WALL_THICKNESS_ROOT = "tasks/asme_b31.3/pipe_wall_thickness_design/root.md"
MAWP_ROOT = "WF-MAWP"

PIPE_WALL_THICKNESS_NODE = "304.1.2-a"

REQUIRED_ASSUMPTION_FIELDS: tuple[str, ...] = (
    "straight_pipe_section",
    "pressure_loading",
)

REQUIRED_USER_INPUTS: tuple[str, ...] = (
    "design_pressure",
    "outside_diameter",
)

REQUIRED_LOOKUP_INPUTS: tuple[str, ...] = (
    "material",
    "design_temperature",
)

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

REQUIRED_PIPE_INPUTS: tuple[str, ...] = (
    "pressure_loading",
    "design_pressure",
    "outside_diameter",
    "material",
    "design_temperature",
)


REQUIRED_MAWP_INPUTS: tuple[str, ...] = (
    "wall_thickness_basis",
    "actual_wall_thickness",
    "corrosion_allowance",
    "outside_diameter",
    "material_grade",
    "design_temperature",
)


def missing_pipe_inputs(stored: dict[str, object]) -> list[str]:
    """Return required pipe wall thickness input ids not yet in stored inputs."""
    return [input_id for input_id in REQUIRED_PIPE_INPUTS if input_id not in stored]


def missing_inputs_for_workflow(
    workflow: str | None,
    stored: dict[str, object],
) -> list[str]:
    """Return workflow-specific missing input ids for agent context."""
    if workflow == "mawp_design":
        return [input_id for input_id in REQUIRED_MAWP_INPUTS if input_id not in stored]
    if workflow == PIPE_WALL_THICKNESS_DESIGN:
        return missing_pipe_inputs(stored)
    return []


def detect_missing_context(message: str) -> list[str]:
    missing: list[str] = []
    for field, pattern in MISSING_CONTEXT_PATTERNS.items():
        if not pattern.search(message):
            missing.append(field)
    return missing
