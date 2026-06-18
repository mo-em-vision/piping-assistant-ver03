"""Lookup engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.lookup_engine import LookupEngine
from engine.reference.standards_paths import resolve_standard_pack


def _lookup_engine() -> LookupEngine:
    root = Path(__file__).resolve().parents[2]
    pack = resolve_standard_pack(root / "standards", "asme_b31.3")
    return LookupEngine(pack)


def test_exact_temperature_lookup() -> None:
    engine = _lookup_engine()
    result = engine.execute_lookup(
        node_id="B313-material-stress",
        lookup_config={
            "table": "tables/material_allowable_stress.yaml",
            "interpolation": True,
        },
        inputs={"material": "SA-106B", "design_temperature": 200, "design_temperature_unit": "F"},
    )

    assert result.calculation.final_result is not None
    assert result.calculation.final_result.value == 193_000_000.0
    assert result.trace.interpolated is False


def test_interpolated_temperature_lookup() -> None:
    engine = _lookup_engine()
    result = engine.execute_lookup(
        node_id="B313-material-stress",
        lookup_config={
            "table": "tables/material_allowable_stress.yaml",
            "interpolation": True,
        },
        inputs={"material": "A106-B", "design_temperature": 150, "design_temperature_unit": "F"},
    )

    assert result.calculation.final_result is not None
    stress = result.calculation.final_result.value
    assert 193_000_000.0 < stress < 207_000_000.0
    assert result.trace.interpolated is True


def test_unknown_material_raises() -> None:
    engine = _lookup_engine()
    with pytest.raises(ValueError, match="Material not found"):
        engine.execute_lookup(
            node_id="B313-material-stress",
            lookup_config={"table": "tables/material_allowable_stress.yaml"},
            inputs={"material": "UNKNOWN", "design_temperature": 200},
        )
