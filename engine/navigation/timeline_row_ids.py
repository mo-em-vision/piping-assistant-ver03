"""Timeline row ids for progress UI (may differ from canonical fact keys)."""

from __future__ import annotations

from engine.reference.parameter_keys import (
    LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
    api_parameter_id,
)

# Canonical storage keys -> user-facing timeline row ids.
_CANONICAL_TO_TIMELINE_ROW: dict[str, str] = {
    LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY: "weld_joint_efficiency",
    "weld_strength_reduction_factor_w": "weld_joint_strength_reduction_factor_W",
    "temperature_coefficient_y": "temperature_coefficient_Y",
}


def timeline_row_id(parameter_key: str) -> str:
    """Map a parameter key to the timeline row id shown in progress UI."""
    canonical = api_parameter_id(parameter_key)
    return _CANONICAL_TO_TIMELINE_ROW.get(canonical, canonical)


def consolidate_timeline_row_ids(ids: set[str]) -> set[str]:
    """Collapse alias keys to one timeline row id per logical parameter."""
    return {timeline_row_id(step_id) for step_id in ids}
