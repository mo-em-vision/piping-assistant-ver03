"""Pipe dimension lookup tests (ASME B36.10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.pipe_dimension_lookup import PipeDimensionLookup


def _lookup() -> PipeDimensionLookup:
    root = Path(__file__).resolve().parents[2] / "standards"
    return PipeDimensionLookup(root)


def test_nps_2_schedule_40_outside_diameter() -> None:
    result = _lookup().lookup("2", schedule="40")
    assert result.nps == "2"
    assert result.schedule == "40"
    assert result.outside_diameter_in == pytest.approx(2.375)
    assert result.wall_thickness_in == pytest.approx(0.154)
    assert result.inner_diameter_in == pytest.approx(2.067)


def test_nps_alias_and_std_schedule() -> None:
    result = _lookup().lookup('2"', schedule="STD")
    assert result.nps == "2"
    assert result.schedule == "40"
    assert result.wall_thickness_in == pytest.approx(0.154)


def test_od_only_lookup_without_schedule() -> None:
    result = _lookup().lookup("4")
    assert result.outside_diameter_in == pytest.approx(4.500)
    assert result.wall_thickness_in is None
    assert result.schedule is None


def test_schedule_80_for_six_inch() -> None:
    result = _lookup().lookup("6", schedule="80")
    assert result.wall_thickness_in == pytest.approx(0.432)
    assert result.inner_diameter_in == pytest.approx(5.761)


def test_unknown_nps_raises() -> None:
    with pytest.raises(ValueError, match="Nominal pipe size not found"):
        _lookup().lookup("99")


def test_unknown_schedule_raises() -> None:
    with pytest.raises(ValueError, match="Schedule"):
        _lookup().lookup("2", schedule="999")
