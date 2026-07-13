"""Contract helpers for lookup-key resolution in API task state."""

from __future__ import annotations

from typing import Any

import pytest

from engine.reference.parameter_keys import LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY
from models.fact import SourceType

PIPE_WALL_LOOKUP_KEY_FIELDS = frozenset(
    {
        "material_grade",
        "design_temperature",
        "nominal_pipe_size",
        "pipe_construction_type",
    }
)

PIPE_WALL_LOOKUP_DERIVED_TIMELINE_STEPS = (
    "outside_diameter",
    "allowable_stress",
    "metallurgical_group",
    "temperature_coefficient_Y",
    LONGITUDINAL_WELD_JOINT_QUALITY_FACTOR_KEY,
    "weld_joint_strength_reduction_factor_W",
)


def fact_source_type(fact: dict[str, Any]) -> str:
    source_type = (fact.get("source") or {}).get("source_type")
    if isinstance(source_type, SourceType):
        return source_type.value
    text = str(source_type or "").strip()
    if text == str(SourceType.TABLE_LOOKUP):
        return SourceType.TABLE_LOOKUP.value
    return text


def timeline_step(state: dict[str, Any], step_id: str) -> dict[str, Any] | None:
    timeline = (state.get("progress") or {}).get("timeline") or []
    return next(
        (step for step in timeline if isinstance(step, dict) and step.get("id") == step_id),
        None,
    )


def assert_pipe_wall_lookup_resolution_in_final_state(state: dict[str, Any]) -> None:
    facts = state.get("facts") or {}
    outputs = state.get("outputs") or {}

    for key in sorted(PIPE_WALL_LOOKUP_KEY_FIELDS):
        assert key in facts, f"missing lookup-key fact {key!r}"

    for key in ("material_grade", "design_temperature", "pipe_construction_type"):
        assert fact_source_type(facts[key]) == SourceType.USER_INPUT.value, (
            f"lookup key {key!r} must remain a user-input fact"
        )

    stress_lookup = outputs.get("allowable_stress_lookup")
    assert isinstance(stress_lookup, dict), "allowable_stress_lookup metadata missing"
    assert stress_lookup.get("table_id") == "asme_b31.3_A-1"
    assert stress_lookup.get("material") == "astm_a106_gr_b"
    assert stress_lookup.get("design_temperature_f") is not None

    od_lookup = outputs.get("outside_diameter_lookup")
    assert isinstance(od_lookup, dict), "outside_diameter_lookup metadata missing"
    assert od_lookup.get("nps") == "6"
    assert od_lookup.get("outside_diameter_mm") == pytest.approx(168.3)

    assert "allowable_stress" in facts
    assert fact_source_type(facts["allowable_stress"]) == SourceType.TABLE_LOOKUP.value
    assert float(outputs.get("allowable_stress") or 0.0) > 0.0

    assert "outside_diameter" in facts
    assert fact_source_type(facts["outside_diameter"]) == SourceType.TABLE_LOOKUP.value

    assert "metallurgical_group" in facts
    metallurgical = facts["metallurgical_group"]
    assert str(metallurgical.get("display_value") or "").lower() == "ferritic_steels"

    for step_id in PIPE_WALL_LOOKUP_DERIVED_TIMELINE_STEPS:
        step = timeline_step(state, step_id)
        assert step is not None, f"missing timeline step for lookup-derived field {step_id!r}"
        assert step.get("status") == "done"
        display = str(step.get("display_value") or "").strip()
        assert display, f"lookup-derived timeline step {step_id!r} must expose display_value"

    stress_step = timeline_step(state, "allowable_stress")
    assert stress_step is not None
    assert "Table A-1" in str(stress_step.get("display_value") or "")

    od_step = timeline_step(state, "outside_diameter")
    assert od_step is not None
    od_display = str(od_step.get("display_value") or "")
    assert "B36.10" in od_display or "168.3" in od_display
