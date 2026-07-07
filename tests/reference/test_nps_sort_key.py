"""Tests for NPS numeric sort order."""

from __future__ import annotations

from engine.reference.pipe_dimensions_db import _nps_sort_key


def test_nps_sort_key_orders_fractional_sizes_after_whole_inches() -> None:
    sizes = ["2-1/2", "3-1/2", "1", "2", "1/2", "3/4", "1-1/4", "3"]
    ordered = sorted(sizes, key=_nps_sort_key)
    assert ordered == ["1/2", "3/4", "1", "1-1/4", "2", "2-1/2", "3", "3-1/2"]
