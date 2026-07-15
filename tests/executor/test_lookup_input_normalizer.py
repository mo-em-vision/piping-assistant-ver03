"""Tests for lookup input canonicalization."""

from __future__ import annotations

import pytest

from engine.executor.lookup_input_normalizer import normalize_lookup_inputs


def test_maps_legacy_material_when_canonical_absent() -> None:
    result = normalize_lookup_inputs({"material": "SA-106B", "design_temperature": 100.0})
    assert result["material_grade"] == "SA-106B"
    assert "material" not in result
    assert result["design_temperature"] == 100.0


def test_keeps_canonical_material_grade() -> None:
    result = normalize_lookup_inputs({"material_grade": "SA-106B"})
    assert result == {"material_grade": "SA-106B"}


def test_rejects_conflicting_material_and_material_grade() -> None:
    with pytest.raises(ValueError, match="Conflicting lookup inputs"):
        normalize_lookup_inputs(
            {"material": "SA-106B", "material_grade": "SA-312"},
        )


def test_allows_matching_material_and_material_grade() -> None:
    result = normalize_lookup_inputs(
        {"material": "SA-106B", "material_grade": "SA-106B"},
    )
    assert result == {"material_grade": "SA-106B"}
